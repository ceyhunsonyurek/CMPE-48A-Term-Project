#!/bin/bash
# Add database indexes for performance optimization
# Run this script on the MySQL VM instance

set -e  # Exit on error

echo "=== Adding Database Indexes ==="

# Add indexes to improve query performance
sudo mysql urlshortener << EOF
-- Index on user_id for faster WHERE user_id = X queries
CREATE INDEX IF NOT EXISTS idx_user_id ON urls(user_id);

-- Composite index for ORDER BY id DESC queries filtered by user_id
CREATE INDEX IF NOT EXISTS idx_user_id_id ON urls(user_id, id DESC);

-- Show indexes
SHOW INDEXES FROM urls;
EOF

echo "=== Indexes Added Successfully ==="
