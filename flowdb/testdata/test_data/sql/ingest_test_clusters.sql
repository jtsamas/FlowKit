/*
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
*/

BEGIN;
DROP TABLE IF EXISTS infrastructure.test_clusters;

CREATE TEMP TABLE temp_clusters (
    longitude NUMERIC,
    latitude NUMERIC,
    cells JSONB
);

COPY temp_clusters (
        longitude,
        latitude,
        cells
    )
FROM
    '/docker-entrypoint-initdb.d/data/infrastructure/cell_clusters.csv'
WITH
    ( DELIMITER ',',
    QUOTE E'\'',
    HEADER true,
    FORMAT csv );

CREATE TABLE infrastructure.test_clusters AS
    SELECT ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) AS geom,
    cells
    FROM temp_clusters;
COMMIT;