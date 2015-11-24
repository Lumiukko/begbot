-- Schema for the BEGBot configuration.

-- Keeps track of the users and their privileges.
create table user (
    id          integer primary key autoincrement not null,
    username    text,
    firstname   text,
    lastname    text,
    telegram_id integer,
    added       date,
    beg         integer,
    admin       integer
);

-- Keeps track of the sessions the bot is active/connected.
create table session (
    id          integer primary key autoincrement not null,
    start       date,
    end         date
);

-- Persists messages in an archive
create table message (
    id          integer primary key autoincrement not null,
    telegram_id integer,
    group_id    integer,
    posted      date,
    content     text,
    type        text
);