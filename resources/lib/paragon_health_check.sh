#!/bin/bash
#############################################
# Paragon TV Library Health Check
# Monitors MySQL library status and health
#############################################

echo "============================================"
echo "Paragon TV Library Health Check"
echo "============================================"
echo "Report Time: $(date)"
echo ""

# Check if we're on master
IP=$(ip addr show | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | cut -d'/' -f1 | head -n1)

if [ "$IP" == "10.0.0.99" ]; then
    echo "Running on: MASTER ($IP)"
    
    # Check Docker/MySQL status
    echo ""
    echo "MySQL Container Status:"
    if docker ps | grep -q mysql-kodi; then
        echo "✓ MySQL container is running"
        
        # Get container stats
        STATS=$(docker stats mysql-kodi --no-stream --format "Memory: {{.MemUsage}} | CPU: {{.CPUPerc}}")
        echo "  $STATS"
    else
        echo "✗ MySQL container is NOT running!"
        exit 1
    fi
else
    echo "Running on: SLAVE ($IP)"
    echo "Checking connection to master..."
    
    # Test MySQL connection
    if timeout 5 bash -c "</dev/tcp/10.0.0.99/3306" 2>/dev/null; then
        echo "✓ Connected to master MySQL"
    else
        echo "✗ Cannot connect to master!"
        exit 1
    fi
fi

# Library Statistics
echo ""
echo "Library Statistics:"
echo "-------------------"

if [ "$IP" == "10.0.0.99" ]; then
    # Get counts directly on master
    MOVIES=$(docker exec mysql-kodi mysql -u kodi -pkodi -sN -e "SELECT COUNT(*) FROM MyVideos107.movie;" 2>/dev/null || echo "0")
    SHOWS=$(docker exec mysql-kodi mysql -u kodi -pkodi -sN -e "SELECT COUNT(*) FROM MyVideos107.tvshow;" 2>/dev/null || echo "0")
    EPISODES=$(docker exec mysql-kodi mysql -u kodi -pkodi -sN -e "SELECT COUNT(*) FROM MyVideos107.episode;" 2>/dev/null || echo "0")
    SONGS=$(docker exec mysql-kodi mysql -u kodi -pkodi -sN -e "SELECT COUNT(*) FROM MyMusic60.song;" 2>/dev/null || echo "0")
    
    echo "Movies:    $MOVIES"
    echo "TV Shows:  $SHOWS"
    echo "Episodes:  $EPISODES"
    echo "Songs:     $SONGS"
    
    # Check for recent additions
    echo ""
    echo "Recent Activity (Last 24 hours):"
    echo "--------------------------------"
    
    # Movies added in last 24 hours
    NEW_MOVIES=$(docker exec mysql-kodi mysql -u kodi -pkodi -sN -e "SELECT COUNT(*) FROM MyVideos107.movie WHERE dateAdded > DATE_SUB(NOW(), INTERVAL 24 HOUR);" 2>/dev/null || echo "0")
    
    # Episodes added in last 24 hours  
    NEW_EPISODES=$(docker exec mysql-kodi mysql -u kodi -pkodi -sN -e "SELECT COUNT(*) FROM MyVideos107.episode WHERE dateAdded > DATE_SUB(NOW(), INTERVAL 24 HOUR);" 2>/dev/null || echo "0")
    
    echo "New Movies:   $NEW_MOVIES"
    echo "New Episodes: $NEW_EPISODES"
    
    # Check for potential issues
    echo ""
    echo "Health Checks:"
    echo "--------------"
    
    # Check for paths that might be offline
    MISSING_PATHS=$(docker exec mysql-kodi mysql -u kodi -pkodi -sN -e "SELECT COUNT(*) FROM MyVideos107.path WHERE strPath LIKE 'smb://%' OR strPath LIKE 'nfs://%';" 2>/dev/null || echo "0")
    if [ "$MISSING_PATHS" -gt 0 ]; then
        echo "⚠ Found $MISSING_PATHS network paths - verify they're accessible"
    else
        echo "✓ All paths appear to be local"
    fi
    
    # Check for orphaned entries
    ORPHAN_FILES=$(docker exec mysql-kodi mysql -u kodi -pkodi -sN -e "SELECT COUNT(*) FROM MyVideos107.files f LEFT JOIN MyVideos107.path p ON f.idPath = p.idPath WHERE p.idPath IS NULL;" 2>/dev/null || echo "0")
    if [ "$ORPHAN_FILES" -gt 0 ]; then
        echo "⚠ Found $ORPHAN_FILES orphaned file entries"
    else
        echo "✓ No orphaned files found"
    fi
    
    # Check active connections
    echo ""
    echo "Active MySQL Connections:"
    echo "-------------------------"
    docker exec mysql-kodi mysql -u root -pparagon -sN -e "SELECT SUBSTRING_INDEX(host, ':', 1) as IP, COUNT(*) as Connections FROM information_schema.processlist WHERE user='kodi' GROUP BY IP;" 2>/dev/null
    
    # Database size
    echo ""
    echo "Database Sizes:"
    echo "---------------"
    docker exec mysql-kodi mysql -u kodi -pkodi -sN -e "SELECT table_schema AS 'Database', ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size_MB' FROM information_schema.tables WHERE table_schema IN ('MyVideos107', 'MyMusic60') GROUP BY table_schema;"
    
else
    # On slave, just show basic connection info
    echo "Slave device - connected to master library"
    echo "Run this script on master (10.0.0.99) for full statistics"
fi

# Check last autopilot run (if log exists)
if [ -f /storage/paragon_autopilot.log ]; then
    echo ""
    echo "Last Autopilot Run:"
    echo "-------------------"
    tail -3 /storage/paragon_autopilot.log
fi

echo ""
echo "============================================"
echo "Health check complete!"
echo "============================================"