USE sacstrsx_24071247;

-- ---------- USERS ----------
-- End users + admin users
CREATE TABLE users (
  user_id        BIGINT PRIMARY KEY AUTO_INCREMENT,
  role           ENUM('CUSTOMER','ADMIN') NOT NULL DEFAULT 'CUSTOMER',
  first_name     VARCHAR(80) NOT NULL,
  last_name      VARCHAR(80) NOT NULL,
  email          VARCHAR(190) NOT NULL,
  phone          VARCHAR(30),
  password_hash  VARCHAR(255) NOT NULL, -- store a hash (bcrypt/argon2 from Flask)
  is_active      TINYINT(1) NOT NULL DEFAULT 1,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_users_email (email)
);

-- ---------- CITIES / HOTELS ----------
-- Your brief is city-based capacity + standard-room peak/off-peak rates. :contentReference[oaicite:4]{index=4}
CREATE TABLE cities (
  city_id   INT PRIMARY KEY AUTO_INCREMENT,
  name      VARCHAR(120) NOT NULL,
  UNIQUE KEY uq_city_name (name)
);

-- One WH hotel per city (simplifies mapping to table 1).
CREATE TABLE hotels (
  hotel_id     INT PRIMARY KEY AUTO_INCREMENT,
  city_id      INT NOT NULL,
  hotel_name   VARCHAR(160) NOT NULL,
  address      VARCHAR(255),
  is_active    TINYINT(1) NOT NULL DEFAULT 1,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_hotels_city (city_id),
  CONSTRAINT fk_hotels_city FOREIGN KEY (city_id) REFERENCES cities(city_id)
);

-- Standard room base rate and total capacity (rooms) per city/hotel. :contentReference[oaicite:5]{index=5}
CREATE TABLE hotel_capacity_rates (
  hotel_id                INT PRIMARY KEY,
  total_rooms             INT NOT NULL,
  standard_peak_gbp       DECIMAL(10,2) NOT NULL,
  standard_offpeak_gbp    DECIMAL(10,2) NOT NULL,
  CONSTRAINT fk_hcr_hotel FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id),
  CONSTRAINT chk_total_rooms CHECK (total_rooms > 0),
  CONSTRAINT chk_rates CHECK (standard_peak_gbp > 0 AND standard_offpeak_gbp > 0)
);

-- ---------- ROOM TYPES ----------
-- 3 room types and rules: 30% standard, 50% double, 20% family. :contentReference[oaicite:6]{index=6}
-- Pricing: double = +20% of standard; optional 2nd guest adds +10% of standard. Family = +50% of standard. :contentReference[oaicite:7]{index=7}
CREATE TABLE room_types (
  room_type_id    TINYINT PRIMARY KEY,
  code            ENUM('STANDARD','DOUBLE','FAMILY') NOT NULL UNIQUE,
  max_guests      TINYINT NOT NULL,
  base_multiplier DECIMAL(5,2) NOT NULL,  -- 1.00, 1.20, 1.50
  second_guest_multiplier DECIMAL(5,2) NOT NULL DEFAULT 0.00, -- only for DOUBLE: 0.10
  CONSTRAINT chk_room_type_mult CHECK (base_multiplier > 0 AND second_guest_multiplier >= 0)
);

ALTER TABLE room_types
MODIFY code VARCHAR(30) NOT NULL;

ALTER TABLE room_types
ADD UNIQUE KEY uq_room_types_code (code);


INSERT INTO room_types(room_type_id, code, max_guests, base_multiplier, second_guest_multiplier) VALUES
(1,'STANDARD',1,1.00,0.00),
(2,'DOUBLE',  2,1.20,0.10),
(3,'FAMILY',  4,1.50,0.00),
(4, 'SINGLE',   1, 0.85, 0.00),
(5, 'DELUXE',   2, 1.35, 0.10),
(6, 'SUITE',    4, 2.00, 0.00),
(7, 'EXECUTIVE',2, 1.60, 0.10);

SELECT * FROM room_types;


-- ---------- ROOM INVENTORY ----------
-- We track inventory as "counts per type per hotel" (fits the capacity+percent requirement).
CREATE TABLE hotel_room_inventory (
  hotel_id       INT NOT NULL,
  room_type_id   TINYINT NOT NULL,
  rooms_count    INT NOT NULL,
  PRIMARY KEY (hotel_id, room_type_id),
  CONSTRAINT fk_hri_hotel FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id),
  CONSTRAINT fk_hri_type  FOREIGN KEY (room_type_id) REFERENCES room_types(room_type_id),
  CONSTRAINT chk_rooms_count CHECK (rooms_count >= 0)
);

SELECT * FROM hotel_room_inventory;

-- ---------- ROOM FEATURES ----------
-- "Each room has specific features such as Wifi, mini-bar, TV, breakfast etc." :contentReference[oaicite:8]{index=8}
CREATE TABLE features (
  feature_id  INT PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE room_type_features (
  hotel_id      INT NOT NULL,
  room_type_id  TINYINT NOT NULL,
  feature_id    INT NOT NULL,
  PRIMARY KEY (hotel_id, room_type_id, feature_id),
  CONSTRAINT fk_rtf_hotel   FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id),
  CONSTRAINT fk_rtf_type    FOREIGN KEY (room_type_id) REFERENCES room_types(room_type_id),
  CONSTRAINT fk_rtf_feature FOREIGN KEY (feature_id) REFERENCES features(feature_id)
);

-- ---------- CURRENCIES + EXCHANGE RATES ----------
-- "prices in user selected currency" + admin manages currencies/exchange rates. :contentReference[oaicite:9]{index=9}
CREATE TABLE currencies (
  currency_code CHAR(3) PRIMARY KEY,     -- e.g. GBP, USD, EUR
  currency_name VARCHAR(60) NOT NULL,
  symbol        VARCHAR(8)
);

-- Exchange rates are "1 GBP -> X currency". (keeps WH base in GBP)
CREATE TABLE exchange_rates (
  currency_code CHAR(3) NOT NULL,
  rate_date     DATE NOT NULL,
  gbp_to_curr   DECIMAL(18,6) NOT NULL,
  PRIMARY KEY(currency_code, rate_date),
  CONSTRAINT fk_xr_curr FOREIGN KEY (currency_code) REFERENCES currencies(currency_code),
  CONSTRAINT chk_rate CHECK (gbp_to_curr > 0)
);

-- ---------- BOOKINGS ----------
-- "Create/view/update/cancel booking"; unique booking ID shown on receipt :contentReference[oaicite:10]{index=10}
-- "Booking can be made up to 3 months in advance" :contentReference[oaicite:11]{index=11}
-- "Max 30 days stay" :contentReference[oaicite:12]{index=12}
CREATE TABLE bookings (
  booking_id        BIGINT PRIMARY KEY AUTO_INCREMENT,
  booking_code      CHAR(12) NOT NULL, -- printable ID for receipt
  user_id           BIGINT NOT NULL,
  hotel_id          INT NOT NULL,

  booking_status    ENUM('PENDING','CONFIRMED','CANCELLED') NOT NULL DEFAULT 'PENDING',
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  check_in          DATE NOT NULL,
  check_out         DATE NOT NULL, -- exclusive (usual hotel convention)

  currency_code     CHAR(3) NOT NULL DEFAULT 'GBP',
  
  -- pricing snapshot fields (in GBP as base)
  standard_rate_gbp        DECIMAL(10,2) NOT NULL, -- the standard rate used (peak/offpeak)
  subtotal_gbp             DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  advance_discount_pct     DECIMAL(5,2)  NOT NULL DEFAULT 0.00,
  advance_discount_gbp     DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  total_gbp                DECIMAL(12,2) NOT NULL DEFAULT 0.00,

-- cancellation snapshots
  cancelled_at             DATETIME NULL,
  cancellation_fee_gbp     DECIMAL(12,2) NULL,
  
  UNIQUE KEY uq_booking_code (booking_code),
  CONSTRAINT fk_book_user  FOREIGN KEY (user_id) REFERENCES users(user_id),
  CONSTRAINT fk_book_hotel FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id),
  CONSTRAINT fk_book_curr  FOREIGN KEY (currency_code) REFERENCES currencies(currency_code),
  CONSTRAINT chk_dates CHECK (check_out > check_in)
);

-- Booking items: which room type(s) + rooms count + guests
-- ("city, dates, number of rooms, room types") :contentReference[oaicite:13]{index=13}
CREATE TABLE booking_rooms (
  booking_room_id  BIGINT PRIMARY KEY AUTO_INCREMENT,
  booking_id       BIGINT NOT NULL,
  room_type_id     TINYINT NOT NULL,
  rooms_qty        INT NOT NULL,
  guests           INT NOT NULL,  -- total guests for this line item
  -- pricing snapshot for the line in GBP
  line_total_gbp   DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  CONSTRAINT fk_br_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
  CONSTRAINT fk_br_type    FOREIGN KEY (room_type_id) REFERENCES room_types(room_type_id),
  CONSTRAINT chk_qty CHECK (rooms_qty > 0),
  CONSTRAINT chk_guests CHECK (guests > 0)
);

-- Simulated payment record (you may “fake” payment per brief). :contentReference[oaicite:14]{index=14}
CREATE TABLE payments (
  payment_id     BIGINT PRIMARY KEY AUTO_INCREMENT,
  booking_id     BIGINT NOT NULL,
  payment_status ENUM('UNPAID','PAID','REFUNDED') NOT NULL DEFAULT 'UNPAID',
  provider       VARCHAR(40) DEFAULT 'SIMULATED',
  paid_at        DATETIME NULL,
  amount_gbp     DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  CONSTRAINT fk_pay_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
);

-- ---------- CANCELLATION EVENTS (audit trail) ----------
-- Needed to "implement handling of cancellation charges and manage it properly in your database." :contentReference[oaicite:15]{index=15}
CREATE TABLE booking_cancellations (
  cancellation_id   BIGINT PRIMARY KEY AUTO_INCREMENT,
  booking_id        BIGINT NOT NULL,
  cancelled_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  days_from_booking INT NOT NULL, -- days between created_at (booking date) and cancelled_at date
  fee_pct           DECIMAL(5,2) NOT NULL,
  fee_amount_gbp    DECIMAL(12,2) NOT NULL,
  reason            VARCHAR(255),
  CONSTRAINT fk_can_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
);

-- Base currency
INSERT INTO currencies(currency_code, currency_name, symbol) VALUES
('GBP','British Pound','£'),
('USD','US Dollar','$'),
('EUR','Euro','€'),
('NP', 'Nepali Rupees', 'NRS');

-- Cities list (Table 1)
INSERT INTO cities(name) VALUES
('Aberdeen'),('Belfast'),('Birmingham'),('Bristol'),('Cardiff'),('Edinburgh'),
('Glasgow'),('London'),('Manchester'),('New Castle'),('Norwich'),('Nottingham'),
('Oxford'),('Plymouth'),('Swansea'),('Bournemouth'),('Kent');

-- One hotel per city
INSERT INTO hotels(city_id, hotel_name)
SELECT city_id, CONCAT('WH ', name) FROM cities;

-- Capacity + rates (standard room GBP peak/offpeak)
-- Peak applies Apr-Aug and Nov-Dec, checked by check-in month. :contentReference[oaicite:17]{index=17}
INSERT INTO hotel_capacity_rates(hotel_id,total_rooms,standard_peak_gbp,standard_offpeak_gbp)
SELECT h.hotel_id,
       CASE c.name
         WHEN 'Aberdeen' THEN 90
         WHEN 'Belfast' THEN 80
         WHEN 'Birmingham' THEN 110
         WHEN 'Bristol' THEN 100
         WHEN 'Cardiff' THEN 90
         WHEN 'Edinburgh' THEN 120
         WHEN 'Glasgow' THEN 140
         WHEN 'London' THEN 160
         WHEN 'Manchester' THEN 150
         WHEN 'New Castle' THEN 90
         WHEN 'Norwich' THEN 90
         WHEN 'Nottingham' THEN 110
         WHEN 'Oxford' THEN 90
         WHEN 'Plymouth' THEN 80
         WHEN 'Swansea' THEN 70
         WHEN 'Bournemouth' THEN 90
         WHEN 'Kent' THEN 100
       END AS total_rooms,
       CASE c.name
         WHEN 'Aberdeen' THEN 140
         WHEN 'Belfast' THEN 130
         WHEN 'Birmingham' THEN 150
         WHEN 'Bristol' THEN 140
         WHEN 'Cardiff' THEN 130
         WHEN 'Edinburgh' THEN 160
         WHEN 'Glasgow' THEN 150
         WHEN 'London' THEN 200
         WHEN 'Manchester' THEN 180
         WHEN 'New Castle' THEN 120
         WHEN 'Norwich' THEN 130
         WHEN 'Nottingham' THEN 130
         WHEN 'Oxford' THEN 180
         WHEN 'Plymouth' THEN 180
         WHEN 'Swansea' THEN 130
         WHEN 'Bournemouth' THEN 130
         WHEN 'Kent' THEN 140
       END AS peak_rate,
       CASE c.name
         WHEN 'Aberdeen' THEN 70
         WHEN 'Belfast' THEN 70
         WHEN 'Birmingham' THEN 75
         WHEN 'Bristol' THEN 70
         WHEN 'Cardiff' THEN 70
         WHEN 'Edinburgh' THEN 80
         WHEN 'Glasgow' THEN 75
         WHEN 'London' THEN 100
         WHEN 'Manchester' THEN 90
         WHEN 'New Castle' THEN 70
         WHEN 'Norwich' THEN 70
         WHEN 'Nottingham' THEN 70
         WHEN 'Oxford' THEN 90
         WHEN 'Plymouth' THEN 90
         WHEN 'Swansea' THEN 70
         WHEN 'Bournemouth' THEN 70
         WHEN 'Kent' THEN 80
       END AS offpeak_rate
FROM hotels h
JOIN cities c ON c.city_id = h.city_id;

-- Helper: fill hotel_room_inventory using percentages
-- Note: We use rounding; adjust as you like to make totals match exactly.
INSERT INTO hotel_room_inventory(hotel_id, room_type_id, rooms_count)
SELECT hotel_id, 1, ROUND(total_rooms * 0.30) FROM hotel_capacity_rates
UNION ALL
SELECT hotel_id, 2, ROUND(total_rooms * 0.50) FROM hotel_capacity_rates
UNION ALL
SELECT hotel_id, 3, total_rooms
              - ROUND(total_rooms * 0.30)
              - ROUND(total_rooms * 0.50)
FROM hotel_capacity_rates;

SELECT room_type_id, code, second_guest_multiplier
FROM room_types;

# Peak/off-peak + advance discount + line price calculation
DELIMITER $$

CREATE FUNCTION fn_is_peak_season(p_check_in DATE)
RETURNS TINYINT DETERMINISTIC
BEGIN
  DECLARE m INT;
  SET m = MONTH(p_check_in);
  RETURN (m BETWEEN 4 AND 8) OR (m IN (11,12));
END$$

DELIMITER $$

DROP FUNCTION IF EXISTS fn_advance_discount_pct$$

CREATE FUNCTION fn_advance_discount_pct(p_booking_date DATE, p_check_in DATE)
RETURNS DECIMAL(5,2) DETERMINISTIC
BEGIN
  DECLARE days_adv INT;
  SET days_adv = DATEDIFF(p_check_in, p_booking_date);

  IF days_adv BETWEEN 80 AND 90 THEN
    RETURN 30.00;
  ELSEIF days_adv BETWEEN 60 AND 79 THEN
    RETURN 20.00;
  ELSEIF days_adv BETWEEN 45 AND 59 THEN
    RETURN 10.00;
  ELSE
    RETURN 0.00;
  END IF;
END$$

DELIMITER ;

-- Nightly price for a given room type & guests count in GBP

DELIMITER $$

CREATE FUNCTION fn_room_line_total_gbp(
  p_standard_rate_gbp DECIMAL(10,2),
  p_room_type_id TINYINT,
  p_rooms_qty INT,
  p_guests INT,
  p_nights INT
)
RETURNS DECIMAL(12,2) DETERMINISTIC
BEGIN
  DECLARE base_mult DECIMAL(5,2);
  DECLARE second_mult DECIMAL(5,2);
  DECLARE max_g INT;
  DECLARE extra_guest_charge DECIMAL(12,2);

  SELECT base_multiplier, second_guest_multiplier, max_guests
    INTO base_mult, second_mult, max_g
  FROM room_types
  WHERE room_type_id = p_room_type_id;

  IF p_guests > (p_rooms_qty * max_g) THEN
    RETURN NULL;
  END IF;

  SET extra_guest_charge = 0.00;

  -- Apply second-guest pricing to ANY room type that has second_guest_multiplier > 0
  IF second_mult > 0 THEN
    SET extra_guest_charge =
      GREATEST(p_guests - p_rooms_qty, 0) * (second_mult * p_standard_rate_gbp);
  END IF;

  RETURN ROUND(
    (
      (p_rooms_qty * (base_mult * p_standard_rate_gbp)) + extra_guest_charge
    ) * p_nights
  , 2);
END$$

DELIMITER ;


# Triggers to enforce rules (3 months advance, max 30 nights)
DELIMITER $$

CREATE TRIGGER trg_bookings_validate_ins
BEFORE INSERT ON bookings
FOR EACH ROW
BEGIN
  DECLARE nights INT;
  DECLARE max_checkin DATE;

  SET nights = DATEDIFF(NEW.check_out, NEW.check_in);
  IF nights <= 0 OR nights > 30 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Stay must be between 1 and 30 nights';
  END IF;

  SET max_checkin = DATE_ADD(DATE(NEW.created_at), INTERVAL 3 MONTH);
  IF NEW.check_in > max_checkin THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Check-in must be within 3 months of booking date';
  END IF;
END$$

CREATE TRIGGER trg_bookings_validate_upd
BEFORE UPDATE ON bookings
FOR EACH ROW
BEGIN
  DECLARE nights INT;

  SET nights = DATEDIFF(NEW.check_out, NEW.check_in);
  IF nights <= 0 OR nights > 30 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Stay must be between 1 and 30 nights';
  END IF;

  -- prevent edits after cancellation
  IF OLD.booking_status = 'CANCELLED' AND NEW.booking_status <> 'CANCELLED' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot reactivate a cancelled booking directly';
  END IF;
END$$

DELIMITER ;

# Stored procedure: create booking + compute totals (DB-managed)
DELIMITER $$

CREATE PROCEDURE sp_create_booking(
  IN p_user_id BIGINT,
  IN p_hotel_id INT,
  IN p_check_in DATE,
  IN p_check_out DATE,
  IN p_currency_code CHAR(3),
  OUT o_booking_id BIGINT,
  OUT o_booking_code CHAR(12)
)
BEGIN
  DECLARE v_peak TINYINT;
  DECLARE v_rate DECIMAL(10,2);
  DECLARE v_disc_pct DECIMAL(5,2);
  DECLARE v_nights INT;

  SET v_nights = DATEDIFF(p_check_out, p_check_in);

  -- pick correct standard rate from hotel_capacity_rates
  SET v_peak = fn_is_peak_season(p_check_in);

  SELECT IF(v_peak=1, standard_peak_gbp, standard_offpeak_gbp)
    INTO v_rate
  FROM hotel_capacity_rates
  WHERE hotel_id = p_hotel_id;

  -- create booking_code like WH0000001234 (12 chars)
  SET o_booking_code = CONCAT('WH', LPAD(FLOOR(RAND()*10000000000), 10, '0'));

  INSERT INTO bookings(
    booking_code, user_id, hotel_id,
    check_in, check_out, currency_code,
    standard_rate_gbp
  )
  VALUES(
    o_booking_code, p_user_id, p_hotel_id,
    p_check_in, p_check_out, p_currency_code,
    v_rate
  );

  SET o_booking_id = LAST_INSERT_ID();

  -- discount percent based on booking_date (created_at) vs check-in
  SELECT fn_advance_discount_pct(DATE(created_at), check_in)
    INTO v_disc_pct
  FROM bookings
  WHERE booking_id = o_booking_id;

  UPDATE bookings
    SET advance_discount_pct = v_disc_pct
  WHERE booking_id = o_booking_id;

  -- Create an UNPAID payment shell
  INSERT INTO payments(booking_id, payment_status, amount_gbp)
  VALUES (o_booking_id, 'UNPAID', 0.00);
END$$

DELIMITER ;

# Add booking room lines + recalc totals
DELIMITER $$

CREATE PROCEDURE sp_add_booking_room(
  IN p_booking_id BIGINT,
  IN p_room_type_id TINYINT,
  IN p_rooms_qty INT,
  IN p_guests INT
)
BEGIN
  DECLARE v_rate DECIMAL(10,2);
  DECLARE v_nights INT;
  DECLARE v_line DECIMAL(12,2);
  DECLARE v_sub DECIMAL(12,2);
  DECLARE v_disc_pct DECIMAL(5,2);
  DECLARE v_disc_amt DECIMAL(12,2);
  DECLARE v_total DECIMAL(12,2);

  SELECT standard_rate_gbp,
         DATEDIFF(check_out, check_in),
         advance_discount_pct
    INTO v_rate, v_nights, v_disc_pct
  FROM bookings
  WHERE booking_id = p_booking_id;

  SET v_line = fn_room_line_total_gbp(v_rate, p_room_type_id, p_rooms_qty, p_guests, v_nights);

  IF v_line IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Guests exceed room capacity for selected type';
  END IF;

  INSERT INTO booking_rooms(booking_id, room_type_id, rooms_qty, guests, line_total_gbp)
  VALUES (p_booking_id, p_room_type_id, p_rooms_qty, p_guests, v_line);

  SELECT COALESCE(SUM(line_total_gbp),0.00) INTO v_sub
  FROM booking_rooms
  WHERE booking_id = p_booking_id;

  SET v_disc_amt = ROUND(v_sub * (v_disc_pct/100.0), 2);
  SET v_total = ROUND(v_sub - v_disc_amt, 2);

  UPDATE bookings
    SET subtotal_gbp = v_sub,
        advance_discount_gbp = v_disc_amt,
        total_gbp = v_total
  WHERE booking_id = p_booking_id;

  UPDATE payments
    SET amount_gbp = v_total
  WHERE booking_id = p_booking_id;
END$$

DELIMITER ;

# Cancellation charges (0%, 50%, 100%) stored + audited
DELIMITER $$

CREATE PROCEDURE sp_cancel_booking(
  IN p_booking_id BIGINT,
  IN p_reason VARCHAR(255)
)
BEGIN
  DECLARE v_created DATE;
  DECLARE v_now DATE;
  DECLARE v_days INT;
  DECLARE v_total DECIMAL(12,2);
  DECLARE v_fee_pct DECIMAL(5,2);
  DECLARE v_fee_amt DECIMAL(12,2);

  SELECT DATE(created_at), total_gbp, booking_status
    INTO v_created, v_total, @status
  FROM bookings
  WHERE booking_id = p_booking_id;

  IF @status = 'CANCELLED' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking already cancelled';
  END IF;

  SET v_now = CURRENT_DATE();
  SET v_days = DATEDIFF(v_now, v_created); -- days since booking date

  IF v_days < 30 THEN
    SET v_fee_pct = 100.00;
  ELSEIF v_days BETWEEN 30 AND 60 THEN
    SET v_fee_pct = 50.00;
  ELSE
    SET v_fee_pct = 0.00;
  END IF;

  SET v_fee_amt = ROUND(v_total * (v_fee_pct/100.0), 2);

  UPDATE bookings
    SET booking_status = 'CANCELLED',
        cancelled_at = CURRENT_TIMESTAMP,
        cancellation_fee_gbp = v_fee_amt
  WHERE booking_id = p_booking_id;

  INSERT INTO booking_cancellations(booking_id, days_from_booking, fee_pct, fee_amount_gbp, reason)
  VALUES (p_booking_id, v_days, v_fee_pct, v_fee_amt, p_reason);

  -- Optional: payment handling (simulate refund)
  -- If fully charged fee=100%, no refund.
  -- If fee=50%, refund 50%.
  -- If fee=0%, refund 100%.
  UPDATE payments
    SET payment_status = CASE
       WHEN v_fee_pct = 100.00 THEN payment_status
       ELSE 'REFUNDED'
    END
  WHERE booking_id = p_booking_id;

END$$

DELIMITER ;

# Availability query (rooms left per type for a date range)
-- Rooms available by hotel & type for a date range
-- (overlap rule: booking overlaps if NOT (existing.check_out <= req_in OR existing.check_in >= req_out))
SELECT
  h.hotel_id,
  h.hotel_name,
  c.name AS city,
  rt.code AS room_type,
  inv.rooms_count
    - COALESCE(SUM(br.rooms_qty), 0) AS rooms_available
FROM hotels h
JOIN cities c ON c.city_id = h.city_id
JOIN hotel_room_inventory inv ON inv.hotel_id = h.hotel_id
JOIN room_types rt ON rt.room_type_id = inv.room_type_id
LEFT JOIN bookings b
  ON b.hotel_id = h.hotel_id
 AND b.booking_status = 'CONFIRMED'
 AND NOT (b.check_out <= '2025-03-10' OR b.check_in >= '2025-03-15')
LEFT JOIN booking_rooms br
  ON br.booking_id = b.booking_id
 AND br.room_type_id = inv.room_type_id
GROUP BY h.hotel_id, rt.code, inv.rooms_count;

SELECT room_type_id, code FROM room_types ORDER BY room_type_id;

INSERT INTO hotel_room_inventory (hotel_id, room_type_id, rooms_count)
SELECT h.hotel_id, rt.room_type_id,
       CASE rt.code
         WHEN 'SINGLE' THEN 10
         WHEN 'DELUXE' THEN 10
         WHEN 'SUITE' THEN 5
         WHEN 'EXECUTIVE' THEN 5
       END
FROM hotels h
JOIN room_types rt
  ON rt.code IN ('SINGLE','DELUXE','SUITE','EXECUTIVE')
LEFT JOIN hotel_room_inventory inv
  ON inv.hotel_id = h.hotel_id AND inv.room_type_id = rt.room_type_id
WHERE inv.hotel_id IS NULL;

SELECT COUNT(*) AS rows_found
FROM hotel_room_inventory
WHERE room_type_id IN (4,5,6,7);

# Currency conversion at query time
-- Convert booking total from GBP to chosen currency using latest available rate <= today
SELECT
  b.booking_id,
  b.booking_code,
  b.total_gbp,
  b.currency_code,
  xr.gbp_to_curr,
  ROUND(b.total_gbp * xr.gbp_to_curr, 2) AS total_in_currency
FROM bookings b
JOIN exchange_rates xr
  ON xr.currency_code = b.currency_code
 AND xr.rate_date = (
   SELECT MAX(rate_date)
   FROM exchange_rates
   WHERE currency_code = b.currency_code
     AND rate_date <= CURRENT_DATE()
 )
ORDER BY b.booking_id DESC
LIMIT 5;

INSERT INTO exchange_rates(currency_code, rate_date, gbp_to_curr)
VALUES
('GBP', CURRENT_DATE(), 1.000000),
('USD', CURRENT_DATE(), 1.25),
('EUR', CURRENT_DATE(), 1.15),
('NP', CURRENT_DATE(), 170.000000);

SELECT * FROM exchange_rates ORDER BY rate_date DESC;


# Admin report queries
-- A) Monthly sales (GBP) - confirmed bookings
SELECT
  DATE_FORMAT(created_at, '%Y-%m') AS ym,
  COUNT(*) AS bookings_count,
  SUM(total_gbp) AS sales_gbp
FROM bookings
WHERE booking_status = 'CONFIRMED'
GROUP BY ym
ORDER BY ym;

-- B) Sales per hotel (GBP)
SELECT
  h.hotel_name,
  c.name AS city,
  COUNT(b.booking_id) AS bookings_count,
  SUM(b.total_gbp) AS sales_gbp
FROM bookings b
JOIN hotels h ON h.hotel_id = b.hotel_id
JOIN cities c ON c.city_id = h.city_id
WHERE b.booking_status = 'CONFIRMED'
GROUP BY h.hotel_id
ORDER BY sales_gbp DESC;

-- C) Top customers by spend
SELECT
  u.user_id,
  CONCAT(u.first_name,' ',u.last_name) AS customer,
  u.email,
  SUM(b.total_gbp) AS total_spend_gbp,
  COUNT(*) AS bookings_count
FROM bookings b
JOIN users u ON u.user_id = b.user_id
WHERE b.booking_status = 'CONFIRMED'
GROUP BY u.user_id
ORDER BY total_spend_gbp DESC
LIMIT 10;

-- D) Cancellation fees collected (GBP)
SELECT
  DATE_FORMAT(cancelled_at, '%Y-%m') AS ym,
  COUNT(*) AS cancellations,
  SUM(cancellation_fee_gbp) AS fees_gbp
FROM bookings
WHERE booking_status = 'CANCELLED'
GROUP BY ym
ORDER BY ym;

SELECT user_id, email, role, is_active
FROM users
WHERE email IN ('singhsaina11@gmail.com', 'singhsaina246@gmail.com');

UPDATE users
SET role='ADMIN'
WHERE email='singhsaina11@gmail.com';

UPDATE users
SET is_active=1
WHERE email='singhsaina11@gmail.com';

INSERT IGNORE INTO features (name) VALUES
('WiFi'),
('TV'),
('Breakfast'),
('Mini-bar'),
('Air Conditioning'),
('Room Service'),
('Gym'),
('Pool');

-- STANDARD (id = 1)
INSERT IGNORE INTO room_type_features (hotel_id, room_type_id, feature_id)
SELECT h.hotel_id, 1, f.feature_id
FROM hotels h
JOIN features f ON f.name IN ('WiFi','TV','Breakfast');

-- DOUBLE (id = 2)
INSERT IGNORE INTO room_type_features (hotel_id, room_type_id, feature_id)
SELECT h.hotel_id, 2, f.feature_id
FROM hotels h
JOIN features f ON f.name IN ('WiFi','TV','Breakfast','Mini-bar');

-- FAMILY (id = 3)
INSERT IGNORE INTO room_type_features (hotel_id, room_type_id, feature_id)
SELECT h.hotel_id, 3, f.feature_id
FROM hotels h
JOIN features f ON f.name IN ('WiFi','TV','Breakfast','Air Conditioning');

-- DELUXE (id = 5)
INSERT IGNORE INTO room_type_features (hotel_id, room_type_id, feature_id)
SELECT h.hotel_id, 5, f.feature_id
FROM hotels h
JOIN features f ON f.name IN ('WiFi','TV','Breakfast','Mini-bar','Room Service');

-- SUITE (id = 6)
INSERT IGNORE INTO room_type_features (hotel_id, room_type_id, feature_id)
SELECT h.hotel_id, 6, f.feature_id
FROM hotels h
JOIN features f ON f.name IN ('WiFi','TV','Breakfast','Mini-bar','Room Service','Pool');

-- EXECUTIVE (id = 7)
INSERT IGNORE INTO room_type_features (hotel_id, room_type_id, feature_id)
SELECT h.hotel_id, 7, f.feature_id
FROM hotels h
JOIN features f ON f.name IN ('WiFi','TV','Breakfast','Mini-bar','Gym');

SELECT
  h.hotel_name,
  c.name AS city,
  rt.code,
  GROUP_CONCAT(f.name ORDER BY f.name SEPARATOR ', ') AS features
FROM room_type_features rtf
JOIN hotels h      ON h.hotel_id = rtf.hotel_id
JOIN cities c      ON c.city_id = h.city_id
JOIN room_types rt ON rt.room_type_id = rtf.room_type_id
JOIN features f    ON f.feature_id = rtf.feature_id
GROUP BY h.hotel_name, c.name, rt.code
ORDER BY c.name, rt.code;

SET SQL_SAFE_UPDATES = 0;

UPDATE hotels h
JOIN cities c ON c.city_id = h.city_id
SET h.address = CASE c.name
  WHEN 'Aberdeen'     THEN 'Union Square, Guild St, Aberdeen AB11 5RG, UK'
  WHEN 'Belfast'      THEN 'Donegall Place, Belfast BT1 5AD, UK'
  WHEN 'Birmingham'   THEN 'Broad Street, Birmingham B1 2HF, UK'
  WHEN 'Bristol'      THEN 'College Green, Bristol BS1 5TR, UK'
  WHEN 'Cardiff'      THEN 'St Mary Street, Cardiff CF10 1AD, UK'
  WHEN 'Edinburgh'    THEN 'Royal Mile, Edinburgh EH1 1QS, UK'
  WHEN 'Glasgow'      THEN 'George Square, Glasgow G2 1DU, UK'
  WHEN 'London'       THEN 'Westminster Bridge Rd, London SE1 7UT, UK'
  WHEN 'Manchester'   THEN 'Deansgate, Manchester M3 4EN, UK'
  WHEN 'New Castle'   THEN 'Grey Street, Newcastle upon Tyne NE1 6EE, UK'
  WHEN 'Norwich'      THEN 'Gentlemans Walk, Norwich NR2 1NA, UK'
  WHEN 'Nottingham'   THEN 'Old Market Square, Nottingham NG1 2DT, UK'
  WHEN 'Oxford'       THEN 'Broad Street, Oxford OX1 3AZ, UK'
  WHEN 'Plymouth'     THEN 'Royal Parade, Plymouth PL1 1DS, UK'
  WHEN 'Swansea'      THEN 'Princess Way, Swansea SA1 3AF, UK'
  WHEN 'Bournemouth'  THEN 'West Cliff Rd, Bournemouth BH2 5PH, UK'
  WHEN 'Kent'         THEN 'High Street, Canterbury, Kent CT1 2JS, UK'
END
WHERE h.hotel_id > 0;

UPDATE hotels h
JOIN cities c ON c.city_id = h.city_id
SET h.address = CASE c.name
  WHEN 'Aberdeen'     THEN 'Union Square, Guild St, Aberdeen AB11 5RG, UK'
  WHEN 'Belfast'      THEN 'Donegall Place, Belfast BT1 5AD, UK'
  WHEN 'Birmingham'   THEN 'Broad Street, Birmingham B1 2HF, UK'
  WHEN 'Bristol'      THEN 'College Green, Bristol BS1 5TR, UK'
  WHEN 'Cardiff'      THEN 'St Mary Street, Cardiff CF10 1AD, UK'
  WHEN 'Edinburgh'    THEN 'Royal Mile, Edinburgh EH1 1QS, UK'
  WHEN 'Glasgow'      THEN 'George Square, Glasgow G2 1DU, UK'
  WHEN 'London'       THEN 'Westminster Bridge Rd, London SE1 7UT, UK'
  WHEN 'Manchester'   THEN 'Deansgate, Manchester M3 4EN, UK'
  WHEN 'New Castle'   THEN 'Grey Street, Newcastle upon Tyne NE1 6EE, UK'
  WHEN 'Norwich'      THEN 'Gentlemans Walk, Norwich NR2 1NA, UK'
  WHEN 'Nottingham'   THEN 'Old Market Square, Nottingham NG1 2DT, UK'
  WHEN 'Oxford'       THEN 'Broad Street, Oxford OX1 3AZ, UK'
  WHEN 'Plymouth'     THEN 'Royal Parade, Plymouth PL1 1DS, UK'
  WHEN 'Swansea'      THEN 'Princess Way, Swansea SA1 3AF, UK'
  WHEN 'Bournemouth'  THEN 'West Cliff Rd, Bournemouth BH2 5PH, UK'
  WHEN 'Kent'         THEN 'High Street, Canterbury, Kent CT1 2JS, UK'
END
WHERE h.hotel_id > 0;

SET SQL_SAFE_UPDATES = 1;

SELECT h.hotel_name, c.name AS city, h.address
FROM hotels h
JOIN cities c ON c.city_id = h.city_id
ORDER BY c.name;

SELECT hotel_id, address FROM hotels ORDER BY hotel_id;

INSERT IGNORE INTO features (name)
VALUES ('Wifi'), ('TV'), ('Breakfast'), ('Mini-bar');

INSERT IGNORE INTO room_type_features (hotel_id, room_type_id, feature_id)
SELECT h.hotel_id, rt.room_type_id, f.feature_id
FROM hotels h
JOIN room_types rt ON rt.code = 'SINGLE'
JOIN features f ON f.name IN ('Wifi', 'TV', 'Breakfast', 'Mini-bar');

SELECT h.hotel_id, rt.code, GROUP_CONCAT(f.name ORDER BY f.name SEPARATOR ', ') AS features
FROM room_type_features rtf
JOIN hotels h ON h.hotel_id = rtf.hotel_id
JOIN room_types rt ON rt.room_type_id = rtf.room_type_id
JOIN features f ON f.feature_id = rtf.feature_id
WHERE rt.code = 'SINGLE'
GROUP BY h.hotel_id, rt.code
ORDER BY h.hotel_id;

UPDATE bookings
SET booking_status = 'CONFIRMED'
WHERE booking_id = 2;

SELECT booking_id, booking_status
FROM bookings
ORDER BY booking_id DESC;

SELECT h.hotel_id, c.name AS city, COUNT(*) AS room_types_count
FROM hotels h
JOIN cities c ON c.city_id = h.city_id
LEFT JOIN hotel_room_inventory inv ON inv.hotel_id = h.hotel_id
GROUP BY h.hotel_id, c.name
ORDER BY room_types_count ASC, c.name;

ALTER TABLE users
ADD COLUMN profile_image VARCHAR(255) NULL;

ALTER TABLE payments
ADD COLUMN payment_method ENUM('CARD','PAYPAL','BANK','CASH')
NULL AFTER provider;
DESCRIBE payments;
SHOW COLUMNS FROM payments LIKE 'payment_method';

CREATE TABLE cookie_preferences (
  user_id   BIGINT NOT NULL,
  necessary BOOLEAN NOT NULL DEFAULT TRUE,
  analytics BOOLEAN NOT NULL DEFAULT FALSE,
  marketing BOOLEAN NOT NULL DEFAULT FALSE,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  CONSTRAINT fk_cookie_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE
);

SHOW TABLES LIKE 'cookie_preferences';
DESCRIBE cookie_preferences;

CREATE TABLE IF NOT EXISTS site_settings (
  setting_key VARCHAR(50) PRIMARY KEY,
  setting_value VARCHAR(255) NOT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- defaults
INSERT INTO site_settings (setting_key, setting_value)
VALUES
  ('site_name', 'World Hotels'),
  ('base_currency', 'GBP')
ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);

 # This query shows how users are stored.
SELECT * FROM users;

# Every booking created on the website is stored here. The booking code is generated automatically.
SELECT booking_id, booking_code, user_id, hotel_id, booking_status, total_gbp
FROM bookings
ORDER BY booking_id DESC; 

# Room types are not stored directly in bookings. They are linked using foreign keys, which is part of normalization.
SELECT b.booking_code, rt.code AS room_type, br.rooms_qty, br.guests
FROM booking_rooms br
JOIN bookings b ON b.booking_id = br.booking_id
JOIN room_types rt ON rt.room_type_id = br.room_type_id;

# City names are stored only once in the cities table to remove transitive dependency.
SELECT * FROM cities;

# Hotels store only city_id, not city names. This prevents data duplication and update anomalies.
SELECT h.hotel_name, c.name AS city
FROM hotels h
JOIN cities c ON h.city_id = c.city_id;

# Room type information is stored separately, which removes partial dependency and supports Second and Third Normal Form.
SELECT room_type_id, code, max_guests, base_multiplier
FROM room_types;

# Features are separated into their own table to avoid repeating columns like WiFi, TV, Breakfast.
SELECT rt.code, GROUP_CONCAT(f.name) AS features
FROM room_type_features rtf
JOIN room_types rt ON rt.room_type_id = rtf.room_type_id
JOIN features f ON f.feature_id = rtf.feature_id
GROUP BY rt.code;

# This procedure handles booking creation, pricing rules, and discount calculation inside the database.
SHOW CREATE PROCEDURE sp_create_booking;

# Triggers enforce business rules like maximum stay length and booking limits
SHOW TRIGGERS;

SELECT user_id, email, role
FROM users
WHERE email IN ('singhsaina11@gmail.com', 'singhsaina246@gmail.com');

INSERT INTO users (
  user_id, role, first_name, last_name, email, phone,
  password_hash, is_active, created_at, updated_at, profile_image
)
VALUES (
  1, 'ADMIN', 'Saina', 'Singh', 'singhsaina11@gmail.com', '9823699349',
  'pbkdf2:sha256:1000000$dc9g0dkw0CsO9bJw$910bf67002c3875601f8732f09ee560028e743d64f0a7311a695cfc14ca93fad',
  1, '2025-12-29 11:59:56', '2026-01-01 23:50:19', 'user_2.png'
);

INSERT INTO users (role, first_name, last_name, email, phone, password_hash, is_active)
VALUES (
  'CUSTOMER',
  'Saina',
  'Singh',
  'singhsaina246@gmail.com',
  '9767661362',
  'pbkdf2:sha256:1000000$Mdz1lk8SJJAz7IFD$635f23d1db0218523abe818412975eab499840a134febf25595f1bda161c8a85',
  1
);

