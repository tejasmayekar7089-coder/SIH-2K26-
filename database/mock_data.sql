-- SIH26188 Seed Data for Simulated Mock Registry

INSERT OR REPLACE INTO mock_registry (document_number, country_code, holder_name, status, issue_date, expiry_date, remarks)
VALUES 
    ('P8923412', 'IND', 'SHARMA, ARJUN', 'VALID', '2022-05-14', '2032-05-13', 'Simulated standard active passport'),
    ('P9999999', 'IND', 'DOE, JOHN', 'STOLEN', '2020-01-01', '2030-01-01', 'Interpol lost/stolen document circular hit'),
    ('W1234567', 'IND', 'MALICIOUS, ACTOR', 'WATCHLIST', '2019-03-10', '2029-03-09', 'Simulated intelligence watchlist notice'),
    ('E4445555', 'IND', 'EXPIRED, USER', 'EXPIRED', '2010-06-01', '2020-05-31', 'Document expired in registry'),
    ('R7778888', 'IND', 'REVOKED, CITIZEN', 'REVOKED', '2021-08-15', '2031-08-14', 'Passport administratively revoked');
