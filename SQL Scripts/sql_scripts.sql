create database pythonproj;
use pythonproj;
commit;

CREATE TABLE users (
    FirstName TEXT,
    LastName TEXT,
    Email VARCHAR(50),
    Password TEXT,
    City VARCHAR(40),
    role VARCHAR(10),
    PRIMARY KEY (Email)
);


CREATE TABLE PASSWORD_RESET (
    Email VARCHAR(50),
    Token VARCHAR(50),
    Timestamp VARCHAR(40),
    FOREIGN KEY (Email)
        REFERENCES users (Email)
        ON DELETE CASCADE
);

CREATE TABLE placedetails (
    placeid INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
    City TEXT,
    PlaceName TEXT,
    Rating FLOAT(2 , 1 ),
    NumberOfReviews INT(3),
    image_name TEXT,
    description TEXT,
    shortdesc TEXT,
    address TEXT,
    review1 TEXT,
    review2 TEXT,
    review3 TEXT,
    latitude TEXT,
    longitude TEXT
);


CREATE TABLE itinerary (
    itinerary_id INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
    email_id VARCHAR(50),
    Date DATE,
    status TEXT,
    city TEXT,
    FOREIGN KEY (email_id)
        REFERENCES users (Email)
        ON DELETE CASCADE
);



CREATE TABLE itinerary_places (
    itinerary_id INT,
    placeid INT,
    sr_no INT,
    FOREIGN KEY (itinerary_id)
        REFERENCES itinerary (itinerary_id)
        ON DELETE CASCADE,
    FOREIGN KEY (placeid)
        REFERENCES placedetails (placeid)
        ON DELETE CASCADE
);


CREATE INDEX token_idx ON PASSWORD_RESET (Token);
CREATE INDEX it_fr_idx ON itinerary_places (itinerary_id);
CREATE INDEX pl_fr_idx ON itinerary_places (placeid);
CREATE INDEX em_fr_idx ON itinerary (email_id);
commit;
