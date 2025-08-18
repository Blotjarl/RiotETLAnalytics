-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS lol_analytics;

-- Use the created database
USE lol_analytics;

-- Create our main table for participant stats
CREATE TABLE IF NOT EXISTS participant_stats (
    matchId BIGINT,
    puuid VARCHAR(100),
    summonerName VARCHAR(100),
    championName VARCHAR(50),
    win BOOLEAN,
    kills INT,
    deaths INT,
    assists INT,
    lp INT,
    ladderRank INT,
    -- A unique key to prevent duplicate entries for the same player in the same match
    PRIMARY KEY (matchId, puuid)
);