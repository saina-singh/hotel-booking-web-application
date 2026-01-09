CREATE DATABASE dvd_rental_practical8;

USE dvd_rental_practical8;

CREATE TABLE Branch (
  branch_no INT PRIMARY KEY AUTO_INCREMENT,
  street VARCHAR(120) NOT NULL,
  city VARCHAR(60) NOT NULL,
  state VARCHAR(60) NOT NULL,
  zip_code VARCHAR(15) NOT NULL,
  telephone VARCHAR(30) NOT NULL
);

CREATE TABLE Staff (
  staff_no INT PRIMARY KEY AUTO_INCREMENT,
  first_name VARCHAR(60) NOT NULL,
  last_name VARCHAR(60) NOT NULL,
  position VARCHAR(60) NOT NULL,
  salary DECIMAL(10,2) NOT NULL,
  branch_no INT NOT NULL,
  CONSTRAINT fk_staff_branch
    FOREIGN KEY (branch_no) REFERENCES Branch(branch_no)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

ALTER TABLE Branch
ADD manager_staff_no INT NULL,
ADD CONSTRAINT fk_branch_manager
  FOREIGN KEY (manager_staff_no) REFERENCES Staff(staff_no)
  ON UPDATE CASCADE
  ON DELETE SET NULL;

CREATE TABLE Member (
  member_no INT PRIMARY KEY AUTO_INCREMENT,
  first_name VARCHAR(60) NOT NULL,
  last_name VARCHAR(60) NOT NULL,
  address VARCHAR(255) NOT NULL,
  date_registered DATE NOT NULL,
  branch_no INT NOT NULL,
  CONSTRAINT fk_member_branch
    FOREIGN KEY (branch_no) REFERENCES Branch(branch_no)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

CREATE TABLE DVD_Catalog (
  catalog_no INT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  category VARCHAR(40) NOT NULL,
  daily_rental DECIMAL(6,2) NOT NULL,
  cost DECIMAL(8,2) NOT NULL,
  status VARCHAR(20) NOT NULL,
  director VARCHAR(120),
  main_actors TEXT
);

CREATE TABLE DVD_Copy (
  dvd_no INT PRIMARY KEY AUTO_INCREMENT,
  catalog_no INT NOT NULL,
  branch_no INT NOT NULL,
  status VARCHAR(20) NOT NULL,
  CONSTRAINT fk_copy_catalog
    FOREIGN KEY (catalog_no) REFERENCES DVD_Catalog(catalog_no)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_copy_branch
    FOREIGN KEY (branch_no) REFERENCES Branch(branch_no)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

CREATE TABLE Rental (
  rental_no INT PRIMARY KEY AUTO_INCREMENT,
  member_no INT NOT NULL,
  dvd_no INT NOT NULL,
  date_out DATE NOT NULL,
  date_returned DATE NULL,
  CONSTRAINT fk_rental_member
    FOREIGN KEY (member_no) REFERENCES Member(member_no)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_rental_dvd
    FOREIGN KEY (dvd_no) REFERENCES DVD_Copy(dvd_no)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);
