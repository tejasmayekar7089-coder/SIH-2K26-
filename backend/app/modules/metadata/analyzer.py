import os
import re
import datetime
from typing import Dict, Any, Tuple, Optional
from PIL import Image, ExifTags

try:
    import exifread
    HAS_EXIFREAD = True
except ImportError:
    HAS_EXIFREAD = False

from app.schemas.metadata import MetadataResult, MetadataClassification
from app.utils.file_utils import detect_file_format, get_mime_type
from app.core.logging import get_logger

logger = get_logger("metadata_analyzer")

KNOWN_EDITING_SOFTWARE_KEYWORDS = [
    "PHOTOSHOP", "GIMP", "CANVA", "PAINT.NET", "PHOTOPEA",
    "LIGHTROOM", "ILLUSTRATOR", "PIXLR", "CORELDRAW", "SNAPSEED"
]

SENSITIVE_GPS_TAGS = {"GPSInfo", "GPSLatitude", "GPSLongitude", "GPSPosition", "EXIF SerialNumber", "BodySerialNumber"}

class IsolatedMetadataAnalyzer:
    """Isolated metadata analyzer extracting EXIF, dimensions, timestamps, and digital file attributes."""

    def analyze_file(self, file_path: str, document_id: str = "") -> MetadataResult:
        """Analyzes file metadata safely without producing a definitive fraud decision."""
        if not os.path.exists(file_path):
            logger.warning(f"File path does not exist for metadata analysis: {file_path}")
            return MetadataResult(
                file_type="UNKNOWN",
                mime_type="application/octet-stream",
                file_size_bytes=0,
                has_exif=False,
                metadata_classification=MetadataClassification.NOT_AVAILABLE,
                supporting_notes="File not found on disk. Metadata NOT_AVAILABLE."
            )

        file_size = os.path.getsize(file_path)
        file_format = detect_file_format(os.path.basename(file_path))
        mime_type = get_mime_type(file_format)

        # 1. Read Image Dimensions & Basic Info
        width, height, aspect_ratio = self._extract_image_dimensions(file_path)

        # 2. Extract EXIF Tags & Metadata
        exif_tags, has_exif = self._extract_exif_tags(file_path)

        # 3. Extract Device Make/Model, Software, and Timestamps
        device_make, device_model = self._extract_device_info(exif_tags)
        software_sig = self._extract_software_signature(exif_tags)
        creation_date, modification_date = self._extract_timestamps(file_path, exif_tags)

        # Log Privacy Safeguard: Log only sanitized info, omit GPS / serials
        sanitized_device = self._sanitize_for_log(device_make, device_model)
        logger.info(f"Metadata analyzed for doc {document_id}: Format={file_format.value}, Has EXIF={has_exif}, Device={sanitized_device}, Software={software_sig or 'None'}")

        # 4. Forensic Classification (SUPPORTING, NOT_AVAILABLE, SUSPICIOUS_METADATA)
        has_editing_sig, is_suspicious = self._evaluate_editing_signatures(software_sig, exif_tags, creation_date)

        if is_suspicious or has_editing_sig:
            classification = MetadataClassification.SUSPICIOUS_METADATA
            notes = "Software editing signature or timestamp anomaly detected. Supporting evidence only (not definitive proof of fraud)."
        elif has_exif and (device_make or device_model or creation_date):
            classification = MetadataClassification.SUPPORTING
            notes = "Direct camera or hardware metadata tags present. Supporting evidence only."
        else:
            classification = MetadataClassification.NOT_AVAILABLE
            notes = "EXIF metadata missing, stripped, or unavailable. Stripped EXIF is normal for web/messaging apps and NOT proof of fraud."

        # Sanitize raw EXIF tags for storage payload (remove sensitive GPS / serials)
        sanitized_raw_tags = self._sanitize_raw_tags(exif_tags)

        return MetadataResult(
            file_type=file_format.value,
            mime_type=mime_type,
            file_size_bytes=file_size,
            has_exif=has_exif,
            image_width=width,
            image_height=height,
            aspect_ratio=aspect_ratio,
            creation_date=creation_date,
            modification_date=modification_date,
            software_signature=software_sig,
            device_make=device_make,
            device_model=device_model,
            exif_raw_tags=sanitized_raw_tags,
            metadata_classification=classification,
            has_editing_signature=has_editing_sig,
            is_recompressed=False,
            supporting_notes=notes
        )

    def _extract_image_dimensions(self, file_path: str) -> Tuple[Optional[int], Optional[int], Optional[float]]:
        """Extracts image width, height, and aspect ratio using Pillow."""
        try:
            with Image.open(file_path) as img:
                w, h = img.size
                aspect_ratio = round(float(w / h), 3) if h > 0 else None
                return w, h, aspect_ratio
        except Exception:
            return None, None, None

    def _extract_exif_tags(self, file_path: str) -> Tuple[Dict[str, Any], bool]:
        """Extracts EXIF tags using ExifRead and Pillow fallbacks."""
        tags_dict: Dict[str, Any] = {}

        # 1. Try ExifRead if available
        if HAS_EXIFREAD:
            try:
                with open(file_path, "rb") as f:
                    exif_data = exifread.process_file(f, details=False)
                    for k, v in exif_data.items():
                        if k not in ("JPEGThumbnail", "TIFFThumbnail"):
                            tags_dict[str(k)] = str(v)
            except Exception as e:
                logger.warning(f"ExifRead parsing error for {file_path}: {e}")

        # 2. Try Pillow Exif fallback
        if not tags_dict:
            try:
                with Image.open(file_path) as img:
                    exif_data = img._getexif()
                    if exif_data:
                        for tag_id, val in exif_data.items():
                            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                            tags_dict[tag_name] = str(val)
            except Exception:
                pass

        has_exif = len(tags_dict) > 0
        return tags_dict, has_exif

    def _extract_device_info(self, tags: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """Extracts camera Make and Model tags."""
        make = None
        model = None
        for k, v in tags.items():
            k_upper = k.upper()
            if "MAKE" in k_upper and not make:
                make = str(v).strip()
            elif "MODEL" in k_upper and not model:
                model = str(v).strip()

        return make, model

    def _extract_software_signature(self, tags: Dict[str, Any]) -> Optional[str]:
        """Extracts Software tag or processing software signature."""
        for k, v in tags.items():
            if "SOFTWARE" in k.upper() or "PROCESSINGSOFTWARE" in k.upper():
                return str(v).strip()
        return None

    def _extract_timestamps(self, file_path: str, tags: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """Extracts creation and modification dates from EXIF or file stat."""
        creation_date = None
        modification_date = None

        # Check EXIF creation date tags
        for k, v in tags.items():
            k_upper = k.upper()
            if "DATETIMEORIGINAL" in k_upper or "DATE TIME ORIGINAL" in k_upper or "CREATEDATE" in k_upper:
                creation_date = str(v).strip()
                break

        # File system mtime fallback for modification date
        try:
            mtime = os.path.getmtime(file_path)
            dt_mtime = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc)
            modification_date = dt_mtime.isoformat()
        except Exception:
            pass

        if not creation_date:
            creation_date = modification_date

        return creation_date, modification_date

    def _evaluate_editing_signatures(self, software_sig: Optional[str], tags: Dict[str, Any], creation_date: Optional[str]) -> Tuple[bool, bool]:
        """Evaluates whether software tag or EXIF anomalies indicate image editing software."""
        has_editing_sig = False
        is_suspicious = False

        if software_sig:
            sw_upper = software_sig.upper()
            if any(kw in sw_upper for kw in KNOWN_EDITING_SOFTWARE_KEYWORDS):
                has_editing_sig = True
                is_suspicious = True

        # Check any raw EXIF tag value for editing software keywords
        for k, v in tags.items():
            v_upper = str(v).upper()
            if any(kw in v_upper for kw in KNOWN_EDITING_SOFTWARE_KEYWORDS):
                has_editing_sig = True
                is_suspicious = True
                break

        # Plausibility check: creation date in future
        if creation_date:
            try:
                # Format: 2026:01:15 10:20:00 or ISO
                clean_dt = creation_date.replace(":", "-", 2)
                dt_obj = datetime.datetime.fromisoformat(clean_dt.replace("Z", "+00:00"))
                if dt_obj > datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1):
                    is_suspicious = True
            except Exception:
                pass

        return has_editing_sig, is_suspicious

    def _sanitize_for_log(self, make: Optional[str], model: Optional[str]) -> str:
        """Sanitizes device info for application logging (omits serials/GPS)."""
        parts = [p for p in (make, model) if p]
        if parts:
            clean_str = " ".join(parts)
            # Remove serial numbers or long hex strings
            clean_str = re.sub(r'\b[0-9a-fA-F]{12,}\b', '[SERIAL_MASKED]', clean_str)
            return clean_str[:40]
        return "Unknown_Device"

    def _sanitize_raw_tags(self, tags: Dict[str, Any]) -> Dict[str, Any]:
        """Removes GPS location tags and device serial numbers from public result payload."""
        sanitized = {}
        for k, v in tags.items():
            if not any(sens in k for sens in SENSITIVE_GPS_TAGS):
                # Stringify payload value
                sanitized[str(k)] = str(v)
        return sanitized
