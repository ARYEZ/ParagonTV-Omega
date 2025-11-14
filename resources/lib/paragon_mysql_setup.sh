#!/bin/bash
#############################################
# Paragon TV MySQL Setup Script
# Run this on the MASTER Kodi (10.0.0.99)
#############################################

echo "==========================================="
echo "Paragon TV MySQL Library Setup - MASTER"
echo "==========================================="

# Check if we're on the master
IP=$(ip addr show | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | cut -d'/' -f1 | head -n1)
if [ "$IP" != "10.0.0.99" ]; then
    echo "WARNING: This doesn't appear to be the master (10.0.0.99)"
    echo "Current IP: $IP"
    echo "Continue anyway? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        exit 1
    fi
fi

# Step 1: Install Docker from LibreELEC repo
echo ""
echo "Step 1: Installing Docker..."
echo "Please install Docker addon manually from:"
echo "Kodi > Add-ons > Install from repository > LibreELEC Add-ons > Services > Docker"
echo ""
echo "Press Enter when Docker addon is installed..."
read

# Step 2: Create necessary directories
echo ""
echo "Step 2: Creating directories..."
mkdir -p /storage/mysql
mkdir -p /storage/paragon_backup

# Step 3: Backup current Kodi database
echo ""
echo "Step 3: Backing up current Kodi databases..."
if [ -d "/storage/.kodi/userdata/Database" ]; then
    cp -r /storage/.kodi/userdata/Database /storage/paragon_backup/
    echo "Backup created at /storage/paragon_backup/Database"
fi

# Step 4: Create Docker startup script
echo ""
echo "Step 4: Creating Docker startup script..."
cat > /storage/.config/autostart.sh << 'AUTOSTART_EOF'
#!/bin/bash
#############################################
# Paragon TV MySQL Container Auto-Start
#############################################

(
    # Wait for network and docker
    sleep 15
    
    # Check if container exists
    if docker ps -a | grep -q mysql-kodi; then
        # Start existing container
        docker start mysql-kodi
    else
        # Create new container
        echo "Starting MySQL container for Kodi..."
        docker run -d \
            --name mysql-kodi \
            --restart unless-stopped \
            -p 3306:3306 \
            -e MYSQL_ROOT_PASSWORD=paragon \
            -e MYSQL_USER=kodi \
            -e MYSQL_PASSWORD=kodi \
            -e MYSQL_DATABASE=MyVideos116 \
            -v /storage/mysql:/var/lib/mysql \
            -v /storage/mysql-init:/docker-entrypoint-initdb.d \
            mariadb:10.5-alpine \
            --max_allowed_packet=16M \
            --key_buffer_size=64M \
            --table_open_cache=256 \
            --sort_buffer_size=4M \
            --net_buffer_length=16K \
            --thread_stack=256K \
            --innodb_buffer_pool_size=128M \
            --skip-name-resolve \
            --bind-address=0.0.0.0
    fi
    
    # Wait for MySQL to be ready
    sleep 10
    
    # Create additional databases if needed
    docker exec mysql-kodi mysql -u root -pparagon -e "CREATE DATABASE IF NOT EXISTS MyMusic72;"
    docker exec mysql-kodi mysql -u root -pparagon -e "CREATE DATABASE IF NOT EXISTS MyVideos116;"
    docker exec mysql-kodi mysql -u root -pparagon -e "GRANT ALL PRIVILEGES ON *.* TO 'kodi'@'%' IDENTIFIED BY 'kodi';"
    docker exec mysql-kodi mysql -u root -pparagon -e "FLUSH PRIVILEGES;"
    
) >> /storage/paragon_mysql.log 2>&1 &
AUTOSTART_EOF

chmod +x /storage/.config/autostart.sh

# Step 5: Create MySQL initialization script
echo ""
echo "Step 5: Creating MySQL init script..."
mkdir -p /storage/mysql-init
cat > /storage/mysql-init/01-init.sql << 'INIT_EOF'
-- Paragon TV MySQL Initialization
CREATE DATABASE IF NOT EXISTS MyVideos116;
CREATE DATABASE IF NOT EXISTS MyMusic72;
GRANT ALL PRIVILEGES ON *.* TO 'kodi'@'%' IDENTIFIED BY 'kodi';
FLUSH PRIVILEGES;
INIT_EOF

# Step 6: Create advancedsettings.xml for master
echo ""
echo "Step 6: Creating advancedsettings.xml..."
mkdir -p /storage/.kodi/userdata
cat > /storage/.kodi/userdata/advancedsettings.xml << 'SETTINGS_EOF'
<advancedsettings>
    <videodatabase>
        <type>mysql</type>
        <host>127.0.0.1</host>
        <port>3306</port>
        <user>kodi</user>
        <pass>kodi</pass>
        <name>MyVideos116</name>
    </videodatabase>
    <musicdatabase>
        <type>mysql</type>
        <host>127.0.0.1</host>
        <port>3306</port>
        <user>kodi</user>
        <pass>kodi</pass>
        <name>MyMusic72</name>
    </musicdatabase>
    <videolibrary>
        <importwatchedstate>true</importwatchedstate>
        <importresumepoint>true</importresumepoint>
    </videolibrary>
</advancedsettings>
SETTINGS_EOF

# Step 7: Start MySQL container now
echo ""
echo "Step 7: Starting MySQL container..."
/storage/.config/autostart.sh

# Wait for container to start
echo "Waiting for MySQL to initialize (30 seconds)..."
sleep 30

# Step 8: Test MySQL connection
echo ""
echo "Step 8: Testing MySQL connection..."
if docker exec mysql-kodi mysql -u kodi -pkodi -e "SHOW DATABASES;" 2>/dev/null | grep -q MyVideos116; then
    echo "✓ MySQL is running and accessible!"
else
    echo "✗ MySQL connection failed. Check /storage/paragon_mysql.log"
fi

echo ""
echo "==========================================="
echo "Master setup complete!"
echo ""
echo "Next steps:"
echo "1. Restart Kodi on this device"
echo "2. Run the slave setup script on all other devices"
echo "3. Your library will be automatically migrated to MySQL"
echo "==========================================="