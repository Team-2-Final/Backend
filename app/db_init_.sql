WHENEVER SQLERROR EXIT FAILURE;
SET ECHO ON;
SET DEFINE OFF;


-- 유저 테이블 생성
CREATE TABLE users (
    id NUMBER PRIMARY KEY,
    username VARCHAR2(50) NOT NULL,
    email VARCHAR2(100) NOT NULL UNIQUE,
    hashed_password VARCHAR2(255) NOT NULL,
    role VARCHAR2(20) DEFAULT 'USER',
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);
-- 유저 테이블용 시퀸스
CREATE SEQUENCE users_seq
START WITH 1
INCREMENT BY 1
NOCACHE
NOCYCLE;
-- 유저 시퀸스 테이블 연결 트리거
CREATE OR REPLACE TRIGGER users_bi
BEFORE INSERT ON users
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT users_seq.NEXTVAL INTO :NEW.id FROM dual;
    END IF;
END;
/

-- 리프레시 토큰 테이블
CREATE TABLE refresh_tokens (
    token_id NUMBER PRIMARY KEY,
    user_id NUMBER NOT NULL,
    refresh_token VARCHAR2(500) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    revoked NUMBER(1) DEFAULT 0 NOT NULL,
    CONSTRAINT fk_refresh_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- 리프레시 토큰 시퀸스
CREATE SEQUENCE refresh_tokens_seq
START WITH 1
INCREMENT BY 1
NOCACHE
NOCYCLE;

-- 리프레시 토큰 테이블 트리거
CREATE OR REPLACE TRIGGER refresh_tokens_bi
BEFORE INSERT ON refresh_tokens
FOR EACH ROW
BEGIN
    IF :NEW.token_id IS NULL THEN
        SELECT refresh_tokens_seq.NEXTVAL INTO :NEW.token_id FROM dual;
    END IF;
END;
/



-- field 재배구역
CREATE TABLE field (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(50) NOT NULL,
    location VARCHAR2(100),
    description VARCHAR2(255)
);
-- field 시퀸스
CREATE SEQUENCE field_seq
START WITH 1
INCREMENT BY 1
NOCACHE
NOCYCLE;
-- field 트리거
CREATE OR REPLACE TRIGGER field_bi
BEFORE INSERT ON field
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT field_seq.NEXTVAL
        INTO :NEW.id
        FROM dual;
    END IF;
END;
/


-- growth_batch(재배시즌)
CREATE TABLE growth_batch (
    id NUMBER PRIMARY KEY,
    field_id NUMBER NOT NULL,
    crop_type VARCHAR2(50) DEFAULT 'tomato',
    start_date DATE,
    end_date DATE,
    description VARCHAR2(255),
    CONSTRAINT fk_growth_batch_field
       FOREIGN KEY (field_id)
       REFERENCES field(id)
);
-- growth_batch(재배시즌) 시퀸스
CREATE SEQUENCE growth_batch_seq
START WITH 1
INCREMENT BY 1
NOCACHE
NOCYCLE;
-- growth_batch 트리거
CREATE OR REPLACE TRIGGER growth_batch_bi
BEFORE INSERT ON growth_batch
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT growth_batch_seq.NEXTVAL
        INTO :NEW.id
        FROM dual;
    END IF;
END;
/


-- environment_data (환경 정보) 테이블
CREATE TABLE environment_data (
    id NUMBER PRIMARY KEY,
    batch_id NUMBER,
    temperature NUMBER,
    humidity NUMBER,
    co2 NUMBER,
    radiation NUMBER,
    soil_ec NUMBER,
    soil_moisture NUMBER,
    ph NUMBER,
    recorded_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_env_batch
        FOREIGN KEY (batch_id)
        REFERENCES growth_batch(id)
        ON DELETE SET NULL
);
-- environment_data (환경 정보) 시퀸스
CREATE SEQUENCE environment_data_seq
START WITH 1
INCREMENT BY 1
NOCACHE
NOCYCLE;
-- environment_data (환경 정보) 트리거
CREATE OR REPLACE TRIGGER environment_data_bi
BEFORE INSERT ON environment_data
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT environment_data_seq.NEXTVAL
        INTO :NEW.id
        FROM dual;
    END IF;
END;
/


-- plant_growth (생장 정보) 테이블
CREATE TABLE plant_growth (
    id NUMBER PRIMARY KEY,
    batch_id NUMBER,
    inference_id VARCHAR2(100),
    model_version VARCHAR2(50),
    plant_height NUMBER,
    leaf_length NUMBER,
    leaf_width NUMBER,
    leaf_count NUMBER,
    captured_at TIMESTAMP,
    inferred_at TIMESTAMP,
    recorded_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_growth_batch
        FOREIGN KEY (batch_id)
        REFERENCES growth_batch(id)
        ON DELETE SET NULL
);
-- plant_growth (생장 정보) 시퀸스
CREATE SEQUENCE plant_growth_seq
START WITH 1
INCREMENT BY 1
NOCACHE
NOCYCLE;
-- plant_growth (생장 정보) 트리거
CREATE OR REPLACE TRIGGER plant_growth_bi
BEFORE INSERT ON plant_growth
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT plant_growth_seq.NEXTVAL
        INTO :NEW.id
        FROM dual;
    END IF;
END;
/



CREATE TABLE ai_result (
    id NUMBER PRIMARY KEY,
    batch_id NUMBER,
    inference_id VARCHAR2(100) NOT NULL,
    model_version VARCHAR2(50),
    result_type VARCHAR2(50) NOT NULL,
    result_value VARCHAR2(100),
    confidence NUMBER,
    severity NUMBER,
    is_alert_sent NUMBER(1) DEFAULT 0,
    captured_at TIMESTAMP,
    inferred_at TIMESTAMP,
    recorded_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_ai_batch
        FOREIGN KEY (batch_id)
        REFERENCES growth_batch(id)
        ON DELETE SET NULL
);
CREATE SEQUENCE ai_result_seq
START WITH 1
INCREMENT BY 1
NOCACHE
NOCYCLE;
CREATE OR REPLACE TRIGGER ai_result_bi
BEFORE INSERT ON ai_result
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT ai_result_seq.NEXTVAL
        INTO :NEW.id
        FROM dual;
    END IF;
END;
/




-- action_log (동작 기록) 테이블
CREATE TABLE action_log (
    id NUMBER PRIMARY KEY,
    batch_id NUMBER,
    action_type VARCHAR2(50),
    action_mode VARCHAR2(20),
    is_on VARCHAR2(10),
    metric VARCHAR2(30),
    trigger_value NUMBER,
    threshold NUMBER,
    status VARCHAR2(20),
    message VARCHAR2(255),
    recorded_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_action_batch
        FOREIGN KEY (batch_id)
        REFERENCES growth_batch(id)
        ON DELETE SET NULL
);
-- action_log (동작 기록) 시퀸스
CREATE SEQUENCE action_log_seq
START WITH 1
INCREMENT BY 1
NOCACHE
NOCYCLE;
-- action_log (동작 기록) 트리거
CREATE OR REPLACE TRIGGER action_log_bi
BEFORE INSERT ON action_log
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT action_log_seq.NEXTVAL
        INTO :NEW.id
        FROM dual;
    END IF;
END;
/



-- image_data (이미지 정보) 테이블
CREATE TABLE image_data (
    id NUMBER PRIMARY KEY,
    batch_id NUMBER,
    inference_id VARCHAR2(100),
    file_path VARCHAR2(255) NOT NULL,
    captured_at TIMESTAMP,
    recorded_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_image_batch
        FOREIGN KEY (batch_id)
        REFERENCES growth_batch(id)
        ON DELETE SET NULL
);
-- image_data (이미지 정보) 시퀸스
CREATE SEQUENCE image_data_seq
START WITH 1
INCREMENT BY 1
NOCACHE
NOCYCLE;
-- image_data (이미지 정보) 트리거
CREATE OR REPLACE TRIGGER image_data_bi
BEFORE INSERT ON image_data
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        SELECT image_data_seq.NEXTVAL
        INTO :NEW.id
        FROM dual;
    END IF;
END;
/

-- 관리자 및 유저 계정(비번1234)
INSERT INTO users (username, email, hashed_password, role)
VALUES ('Admin', 'admin1234@test.com', '$2b$12$zXHMufHslzkN3Q8rLGI.zeyL5U6whLHzopSiaOeUZPnWrD.PgGaMe', 'ADMIN');
INSERT INTO users (username, email, hashed_password, role)
VALUES ('Normal_User', 'user1234@test.com', '$2b$12$zXHMufHslzkN3Q8rLGI.zeyL5U6whLHzopSiaOeUZPnWrD.PgGaMe', 'USER');


-- 필드 추가
INSERT INTO field (name, location, description)
VALUES ('Cheonan Center 1', 'Cheonan', 'main center');
INSERT INTO field (name, location, description)
VALUES ('Cheonan Center 2', 'Cheonan', 'Seedling Production');
INSERT INTO field (name, location, description)
VALUES ('Cheonan Center 3', 'Cheonan', 'Research and Development');
INSERT INTO field (name, location, description)
VALUES ('Cheonan Center 4', 'Cheonan', 'Underground Production Facility');

-- 생육 단계 관리(GROWTH BATCH) 추가
INSERT INTO growth_batch (field_id, crop_type, description)
VALUES (1, 'tomato', 'first batch');

PROMPT === DB INIT DONE ===

commit;
