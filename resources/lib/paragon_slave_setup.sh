# Create the slave setup script
cat > /storage/paragon_slave_setup.sh << 'EOF'
#!/bin/bash
echo "==========================================="
echo "Paragon TV MySQL Library Setup - SLAVE"
echo "==========================================="

# Get current IP
IP=$(ip addr show | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | cut -d'/' -f1 | head -n1)
echo "Current device IP: $IP"

if [ "$IP" == "10.0.0.99" ]; then
    echo "This is the master device! Exiting."
    exit 1
fi

# Test connection to master
echo "Testing connection to master..."
if ping -c 3 10.0.0.99 > /dev/null 2>&1; then
    echo "✓ Master is reachable"
else
    echo "✗ Cannot reach master"
    exit 1
fi

# Backup current database
mkdir -p /storage/paragon_backup
if [ -d "/storage/.kodi/userdata/Database" ]; then
    cp -r /storage/.kodi/userdata/Database /storage/paragon_backup/
    echo "Backup created"
fi

# Create advancedsettings.xml
mkdir -p /storage/.kodi/userdata
cat > /storage/.kodi/userdata/advancedsettings.xml << 'SETTINGS'
<advancedsettings>
    <videodatabase>
        <type>mysql</type>
        <host>10.0.0.99</host>
        <port>3306</port>
        <user>kodi</user>
        <pass>kodi</pass>
        <n>MyVideos116</n>
    </videodatabase>
    <musicdatabase>
        <type>mysql</type>
        <host>10.0.0.99</host>
        <port>3306</port>
        <user>kodi</user>
        <pass>kodi</pass>
        <n>MyMusic72</n>
    </musicdatabase>
    <videolibrary>
        <importwatchedstate>true</importwatchedstate>
        <importresumepoint>true</importresumepoint>
    </videolibrary>
</advancedsettings>
SETTINGS

echo "Setup complete! Restart Kodi to connect to shared library."
EOF

chmod +x /storage/paragon_slave_setup.sh