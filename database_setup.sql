# Database setup script
# Run this in your MySQL client to create the necessary tables

CREATE TABLE IF NOT EXISTS free_internship (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    usn VARCHAR(50) NOT NULL UNIQUE,
    resume LONGBLOB,
    project LONGBLOB,
    id_card LONGBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usn (usn)
);

CREATE TABLE IF NOT EXISTS paid_internship (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    usn VARCHAR(50) NOT NULL UNIQUE,
    resume LONGBLOB,
    project LONGBLOB,
    id_card LONGBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usn (usn)
);

-- Verify tables were created
SHOW TABLES LIKE '%internship%';

-- Optional: Insert sample data
-- INSERT INTO free_internship (name, usn) VALUES ('John Doe', 'USN001');
-- INSERT INTO paid_internship (name, usn) VALUES ('Jane Smith', 'USN002');
