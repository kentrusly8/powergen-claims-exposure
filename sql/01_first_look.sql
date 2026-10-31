.headers on
.mode column

-- 1. How many claims are there in total, and how many have no plant ID?
SELECT COUNT(*) AS total_claims,
       SUM(plant_id = '') AS missing_plant_id
FROM raw_claims;

-- 2. How many claims link to a plant by exact ID? (first matching tier)
SELECT COUNT(*) AS total_claims,
       COUNT(e.plant_id) AS exact_id_match
FROM raw_claims AS c
LEFT JOIN raw_exposure AS e ON c.plant_id = e.plant_id;

-- 3. Which claim IDs appear more than once? (duplicates)
SELECT claim_id, COUNT(*) AS times
FROM raw_claims
GROUP BY claim_id
HAVING COUNT(*) > 1;

-- 4. How is technology written in the claims?
SELECT technology, COUNT(*) AS claims
FROM raw_claims
GROUP BY technology
ORDER BY claims DESC;

