DROP DATABASE IF EXISTS ev_project;

CREATE DATABASE ev_project;

USE ev_project;

CREATE TABLE ev_bunks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bunk_name VARCHAR(255) NOT NULL UNIQUE,
    owner_name VARCHAR(255) NOT NULL,
    state VARCHAR(255) NOT NULL,
    city VARCHAR(255) NOT NULL,
    address TEXT,
    total_machines INT DEFAULT 0,
    fast_chargers INT DEFAULT 0,
    normal_chargers INT DEFAULT 0,
    damaged_machines INT DEFAULT 0,
    working_machines INT DEFAULT 0,
    contact VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE slot_bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bunk_name VARCHAR(255),
    customer_name VARCHAR(255),
    phone VARCHAR(20),
    vehicle_type VARCHAR(100),
    slot_date DATE,
    slot_time TIME,
    charging_type VARCHAR(50),
    estimated_price FLOAT,
    advance_amount DECIMAL(10,2),
    payment_method VARCHAR(50),
    payment_status VARCHAR(50) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(255),
    email VARCHAR(255),
    username VARCHAR(255) UNIQUE,
    password VARCHAR(255),
    role VARCHAR(50) DEFAULT 'User',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, password, role)
VALUES
('admin', 'admin123', 'Admin'),
('user', 'user123', 'User');

INSERT INTO ev_bunks
(
    bunk_name,
    owner_name,
    state,
    city,
    address,
    total_machines,
    fast_chargers,
    normal_chargers,
    damaged_machines,
    working_machines,
    contact
)
VALUES
(
    'ChargeX EV Station',
    'Rahul Sharma',
    'West Bengal',
    'Kolkata',
    'Salt Lake Sector V',
    10,
    4,
    6,
    1,
    9,
    '9876543210'
),
(
    'GreenCharge EV Hub',
    'Ankit Verma',
    'Delhi',
    'New Delhi',
    'Connaught Place',
    12,
    5,
    7,
    2,
    10,
    '9123456780'
),
(
    'PowerGrid EV Point',
    'Sanjay Kumar',
    'Maharashtra',
    'Mumbai',
    'Andheri East',
    15,
    7,
    8,
    3,
    12,
    '9988776655'
);

SELECT * FROM ev_bunks;
SELECT * FROM users;
SELECT * FROM slot_bookings;