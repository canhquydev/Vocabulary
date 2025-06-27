
CREATE TABLE account (
    id SERIAL PRIMARY KEY, -- SERIAL tự động tăng cho id
    username VARCHAR(20) NOT NULL,
    password VARCHAR(20) NOT NULL,
    roles VARCHAR(20) NOT NULL,
    active INTEGER NOT NULL
);

CREATE TABLE vocabulary (
    id SERIAL PRIMARY KEY, -- SERIAL tự động tăng cho id
    word VARCHAR(50) NOT NULL,
    mean VARCHAR(100) NOT NULL
);

-- drop table account; -- Chỉ dùng khi cần xóa bảng

SELECT * FROM account; -- Chỉ dùng để kiểm tra

INSERT INTO account (username, password, roles, active) VALUES ('test', '123456', 'admin', 1);