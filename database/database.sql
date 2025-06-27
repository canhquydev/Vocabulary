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
drop table account
select * from account
insert into account values('test', '123456', 'admin', 1)


