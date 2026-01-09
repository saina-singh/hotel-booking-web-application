CREATE DATABASE practical8;

USE practical8;

CREATE TABLE Book (
  isbn VARCHAR(20) PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  edition VARCHAR(30),
  pub_year INT
);

CREATE TABLE Borrower (
  borrower_no INT PRIMARY KEY AUTO_INCREMENT,
  borrower_name VARCHAR(120) NOT NULL,
  address VARCHAR(255) NOT NULL
);

CREATE TABLE BookCopy (
  copy_no INT PRIMARY KEY AUTO_INCREMENT,
  isbn VARCHAR(20) NOT NULL,
  status VARCHAR(20) NOT NULL,
  allowable_loan_period INT NOT NULL,
  CONSTRAINT fk_copy_book
    FOREIGN KEY (isbn) REFERENCES Book(isbn)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

CREATE TABLE Loan (
  loan_no INT PRIMARY KEY AUTO_INCREMENT,
  borrower_no INT NOT NULL,
  copy_no INT NOT NULL,
  date_loaned DATE NOT NULL,
  date_returned DATE NULL,
  CONSTRAINT fk_loan_borrower
    FOREIGN KEY (borrower_no) REFERENCES Borrower(borrower_no)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_loan_copy
    FOREIGN KEY (copy_no) REFERENCES BookCopy(copy_no)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);
