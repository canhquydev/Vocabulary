use master
create database QL
use QL
create table account(
	id int identity not null primary key,
	username nchar(20) not null,
	password nvarchar(20) not null,
	roles nvarchar(20) not null,
	active int not null
)

create table vocabulary(
	id int identity not null primary key,
	word nvarchar(50) not null,
	mean nvarchar(100) not null
)

INSERT INTO vocabulary (word, mean) VALUES ('Touchpad', N'Chuột cảm ứng (của máy tính xách tay)');
INSERT INTO vocabulary (word, mean) VALUES ('Webcam', N'Webcam');
INSERT INTO vocabulary (word, mean) VALUES ('Touch screen', N'Màn hình cảm ứng');
INSERT INTO vocabulary (word, mean) VALUES ('Digital camera', N'Máy ảnh kỹ thuật số');
INSERT INTO vocabulary (word, mean) VALUES ('Camcorder', N'Máy quay');
INSERT INTO vocabulary (word, mean) VALUES ('Barcode reader', N'Đầu đọc mã vạch');
INSERT INTO vocabulary (word, mean) VALUES ('Grab', N'(v) giữ, nắm giữ, lấy (cái gì đó)');
INSERT INTO vocabulary (word, mean) VALUES ('Select', N'(v) lựa chọn, chọn');
INSERT INTO vocabulary (word, mean) VALUES ('Drag', N'(v) Kéo, rê');
INSERT INTO vocabulary (word, mean) VALUES ('Double click', N'(v) nhấn đúp, kích đúp');
INSERT INTO vocabulary (word, mean) VALUES ('Light pen', N'Bút quang');
INSERT INTO vocabulary (word, mean) VALUES ('Graphics tablet', N'Bảng vẽ đồ họa');
INSERT INTO vocabulary (word, mean) VALUES ('Scanner', N'Máy quét');
INSERT INTO vocabulary (word, mean) VALUES ('Microphone', N'Micro');
INSERT INTO vocabulary (word, mean) VALUES ('Monitor', N'Màn hình máy tính');
INSERT INTO vocabulary (word, mean) VALUES ('Resolution', N'(n) Độ phân giải');
INSERT INTO vocabulary (word, mean) VALUES ('Screen size', N'Kích cỡ màn hình');
INSERT INTO vocabulary (word, mean) VALUES ('Aspect ratio', N'Tỷ lệ màn hình');
INSERT INTO vocabulary (word, mean) VALUES ('Color depth', N'(n) Độ sâu màu sắc');
INSERT INTO vocabulary (word, mean) VALUES ('Refresh rate', N'(n) Tần số làm tươi màn hình');
INSERT INTO vocabulary (word, mean) VALUES ('Response time', N'(n) Thông số phản hồi tín hiệu');
INSERT INTO vocabulary (word, mean) VALUES ('Liquid crystal display', N'Màn hình tinh thể lỏng');
INSERT INTO vocabulary (word, mean) VALUES ('Keyboard', N'Bàn phím');
INSERT INTO vocabulary (word, mean) VALUES ('Arrow key', N'Phím mũi tên');
INSERT INTO vocabulary (word, mean) VALUES ('Cursor control key', N'Phím điều khiển con trỏ');
INSERT INTO vocabulary (word, mean) VALUES ('Alphanumeric keys', N'Các phím số và chữ');
INSERT INTO vocabulary (word, mean) VALUES ('Function key', N'Phím chức năng');
INSERT INTO vocabulary (word, mean) VALUES ('Dedicated key', N'Phím chuyên dụng');
INSERT INTO vocabulary (word, mean) VALUES ('Numeric keypad', N'Phím dệm số');
INSERT INTO vocabulary (word, mean) VALUES ('Mouse', N'Chuột máy tính');
INSERT INTO vocabulary (word, mean) VALUES ('Right mouse button', N'Phím chuột phải');
INSERT INTO vocabulary (word, mean) VALUES ('Left mouse button', N'Phím chuột trái');
INSERT INTO vocabulary (word, mean) VALUES ('Scroll wheel', N'Con lăn');
INSERT INTO vocabulary (word, mean) VALUES ('Palm rest', N'Chỗ đặt bàn tay (trên chuột, bàn phím)');
INSERT INTO vocabulary (word, mean) VALUES ('Flat screen', N'Màn hình phẳng');
INSERT INTO vocabulary (word, mean) VALUES ('Plasma screen', N'Màn hình plasma');
INSERT INTO vocabulary (word, mean) VALUES ('High Definition Multimedia Interface (HDMI) cable', N'Cáp kết nối HDMI');
INSERT INTO vocabulary (word, mean) VALUES ('Video graphics adapter (VGA) cable', N'Cáp kết nối VGA');
INSERT INTO vocabulary (word, mean) VALUES ('Printer', N'Máy in');
INSERT INTO vocabulary (word, mean) VALUES ('Speaker', N'Loa');
INSERT INTO vocabulary (word, mean) VALUES ('Projector', N'Máy chiếu');

DBCC CHECKIDENT ('vocabulary', RESEED, 0);
drop table account
select * from account
select * from vocabulary
delete from vocabulary
insert into account values('test', '123456', 'admin', 1)


