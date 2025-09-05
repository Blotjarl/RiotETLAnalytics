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

-- Create the new table with the columns provided by the API
CREATE TABLE IF NOT EXISTS players (
    puuid VARCHAR(100) NOT NULL,
    leaderboardRank INT,
    leaguePoints INT,
    `rank` VARCHAR(10), -- The tier rank, e.g., "I"
    wins INT,
    losses INT,
    veteran BOOLEAN,
    inactive BOOLEAN,
    freshBlood BOOLEAN,
    hotStreak BOOLEAN,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (puuid)
);


