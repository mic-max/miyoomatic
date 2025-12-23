CREATE TABLE IF NOT EXISTS encounters (
    -- TODO: include timestamp info into PK
    encounter_id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL,
    method_id INTEGER NOT NULL,
    pokemon_id INTEGER NOT NULL,
    shiny INTEGER NOT NULL,
    level INTEGER,
    gender INTEGER,
    FOREIGN KEY (location_id) REFERENCES locations (location_id)
);

CREATE TABLE IF NOT EXISTS locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    encounter_rate INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS spawns (
    spawn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL,
    method_id INTEGER NOT NULL,
    pokemon_id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    odds INTEGER NOT NULL,
    FOREIGN KEY (location_id) REFERENCES locations (location_id)
);

-- index pokemon.name to quickly search
-- male_odds INTEGER -- 8 means 100% male, 0 means 100% female, 4 is 50/50, NULL is gender unknown

-- keep color_id == 0, this can be used to determine percentages since I know the image is 64x64, i can
--  also just cool for organizing sprites by background
--  assuming a square sprite this information can be determined by 4096 - sum of all other pixel color counts.
-- 4,096 pixels total and 2500 pixels of color0 means that the actual sprite is only ~1600 pixels and i can use that
-- number to measure what percent of the sprite is a certain color?
-- maybe the sprite isn't saved as a 64x64 in the games ROM?
CREATE TABLE IF NOT EXISTS palettes (
    pokemon_id INTEGER NOT NULL,
    color INTEGER NOT NULL,
    count INTEGER NOT NULL
);

-- TODO symbols like nidoran m/f, mr. mime period, farfetch'd apostrophe

INSERT INTO locations (location_id, name, encounter_rate) VALUES
(99, 'Pokemon Tower 3F', 10);

-- Pokemon Tower 3F uses 11/12 spawn slots.
INSERT INTO spawns (location_id, method_id, pokemon_id, level, odds) VALUES
(99, 0, 92, 13, 51),
(99, 0, 92, 14, 51),
(99, 0, 92, 15, 25),
(99, 0, 92, 16, 25),
(99, 0, 92, 17, 25),
(99, 0, 92, 18, 25),
(99, 0, 92, 19, 26), -- I combined two slots into one
(99, 0, 104, 15, 10),
(99, 0, 104, 17, 10),
(99, 0, 93, 25, 3);
