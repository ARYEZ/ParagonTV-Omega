#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#      Copyright (C) 2025 Aryez
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import xbmc, xbmcaddon
import os
import sys

ADDON_ID = 'script.paragontv'
ADDON = xbmcaddon.Addon(ADDON_ID)
ADDON_PATH = ADDON.getAddonInfo('path')

def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log('[PTV Maintenance Action] ' + str(msg), level)

def notify(msg, title='PTV Maintenance'):
    xbmc.executebuiltin('Notification({}, {}, 5000)'.format(title, msg))

def execute_maintenance(schedule_id=None):
    if not schedule_id:
        log('No schedule ID provided')
        return
    
    log('Maintenance started for Schedule {}'.format(schedule_id))
    show_notification = ADDON.getSetting('MaintenanceNotification') == 'true'
    
    if show_notification:
        notify('Maintenance started for Schedule {}'.format(schedule_id))
    
    # Track which tasks are completed
    tasks_completed = []
    
    # 1. NFO Rename - Bumpers
    if ADDON.getSetting('MaintenanceNFOBumpers{}'.format(schedule_id)) == 'true':
        log('Running NFO renamer for Bumpers for Schedule {}'.format(schedule_id))
        if show_notification:
            notify('Renaming Bumper files...')
        
        # Get the bumpers directory from settings
        bumpers_dir = ADDON.getSetting('NFOBumpersPath')
        if bumpers_dir:
            nfo_script = os.path.join(ADDON_PATH, 'resources', 'lib', 'nfo_renamer_bumpers.py')
            if os.path.exists(nfo_script):
                xbmc.executebuiltin('RunScript({}, {})'.format(nfo_script, bumpers_dir))
                xbmc.sleep(10000)  # Wait 10 seconds for bumpers
                tasks_completed.append('Bumpers Renamed')
            else:
                log('NFO renamer bumpers script not found: {}'.format(nfo_script))
                if show_notification:
                    notify('Bumpers script not found', 'Error')
        else:
            log('Bumpers directory not configured')
            if show_notification:
                notify('Bumpers directory not set', 'Warning')
    
    # 2. NFO Rename - Movies  
    if ADDON.getSetting('MaintenanceNFOMovies{}'.format(schedule_id)) == 'true':
        log('Running NFO renamer for Movies for Schedule {}'.format(schedule_id))
        if show_notification:
            notify('Renaming Movie files...')
        
        # Get the movies directory from settings
        movies_dir = ADDON.getSetting('NFOMoviesPath')
        if movies_dir:
            nfo_script = os.path.join(ADDON_PATH, 'resources', 'lib', 'nfo_renamer_movies.py')
            if os.path.exists(nfo_script):
                # Add --recursive flag for movies (subdirectories)
                xbmc.executebuiltin('RunScript({}, {}, --recursive)'.format(nfo_script, movies_dir))
                xbmc.sleep(15000)  # Wait 15 seconds for movies
                tasks_completed.append('Movies Renamed')
            else:
                log('NFO renamer movies script not found: {}'.format(nfo_script))
                if show_notification:
                    notify('Movies script not found', 'Error')
        else:
            log('Movies directory not configured')
            if show_notification:
                notify('Movies directory not set', 'Warning')
    
    # 3. NFO Rename - Television
    if ADDON.getSetting('MaintenanceNFOTelevision{}'.format(schedule_id)) == 'true':
        log('Running NFO renamer for Television for Schedule {}'.format(schedule_id))
        if show_notification:
            notify('Renaming TV Show files...')
        
        # Get the TV shows directory from settings
        tv_dir = ADDON.getSetting('NFOTelevisionPath')
        if tv_dir:
            nfo_script = os.path.join(ADDON_PATH, 'resources', 'lib', 'nfo_renamer_television.py')
            if os.path.exists(nfo_script):
                # Add --recursive flag for TV shows (subdirectories)
                xbmc.executebuiltin('RunScript({}, {}, --recursive)'.format(nfo_script, tv_dir))
                xbmc.sleep(20000)  # Wait 20 seconds for TV shows
                tasks_completed.append('TV Shows Renamed')
            else:
                log('NFO renamer television script not found: {}'.format(nfo_script))
                if show_notification:
                    notify('TV Shows script not found', 'Error')
        else:
            log('Television directory not configured')
            if show_notification:
                notify('TV Shows directory not set', 'Warning')
    
    # 4. Update Video Library
    if ADDON.getSetting('MaintenanceVideoLibrary{}'.format(schedule_id)) == 'true':
        log('Updating video library for Schedule {}'.format(schedule_id))
        if show_notification:
            notify('Updating video library...')
        
        xbmc.executebuiltin('UpdateLibrary(video)')
        xbmc.sleep(5000)  # Wait 5 seconds for scan to start
        
        # Wait for scan to complete (max 5 minutes)
        max_wait = 300
        waited = 0
        while xbmc.getCondVisibility('Library.IsScanningVideo') and waited < max_wait:
            xbmc.sleep(1000)
            waited += 1
        
        tasks_completed.append('Video Library Updated')
        
        # Clean video library if enabled
        if ADDON.getSetting('MaintenanceCleanVideo{}'.format(schedule_id)) == 'true':
            log('Cleaning video library for Schedule {}'.format(schedule_id))
            if show_notification:
                notify('Cleaning video library...')
            
            xbmc.executebuiltin('CleanLibrary(video)')
            xbmc.sleep(5000)  # Wait 5 seconds for clean to start
            
            # Wait for clean to complete (max 5 minutes)
            waited = 0
            while xbmc.getCondVisibility('Library.IsScanningVideo') and waited < max_wait:
                xbmc.sleep(1000)
                waited += 1
            
            tasks_completed.append('Video Library Cleaned')
    
    # 5. Update Music Library
    if ADDON.getSetting('MaintenanceMusicLibrary{}'.format(schedule_id)) == 'true':
        log('Updating music library for Schedule {}'.format(schedule_id))
        if show_notification:
            notify('Updating music library...')
        
        xbmc.executebuiltin('UpdateLibrary(music)')
        xbmc.sleep(5000)  # Wait 5 seconds for scan to start
        
        # Wait for scan to complete (max 5 minutes)
        max_wait = 300
        waited = 0
        while xbmc.getCondVisibility('Library.IsScanningMusic') and waited < max_wait:
            xbmc.sleep(1000)
            waited += 1
        
        tasks_completed.append('Music Library Updated')
        
        # Clean music library if enabled
        if ADDON.getSetting('MaintenanceCleanMusic{}'.format(schedule_id)) == 'true':
            log('Cleaning music library for Schedule {}'.format(schedule_id))
            if show_notification:
                notify('Cleaning music library...')
            
            xbmc.executebuiltin('CleanLibrary(music)')
            xbmc.sleep(5000)  # Wait 5 seconds for clean to start
            
            # Wait for clean to complete (max 5 minutes)
            waited = 0
            while xbmc.getCondVisibility('Library.IsScanningMusic') and waited < max_wait:
                xbmc.sleep(1000)
                waited += 1
            
            tasks_completed.append('Music Library Cleaned')
    
    # 6. Organize Channels
    if ADDON.getSetting('MaintenanceOrganizeChannels{}'.format(schedule_id)) == 'true':
        log('Running channel organizer for Schedule {}'.format(schedule_id))
        if show_notification:
            notify('Organizing channels...')
        
        organizer_script = os.path.join(ADDON_PATH, 'resources', 'lib', 'channel_organizer.py')
        if os.path.exists(organizer_script):
            xbmc.executebuiltin('RunScript({})'.format(organizer_script))
            xbmc.sleep(2000)  # Give it a moment to start
            tasks_completed.append('Channels Organized')
    
    # 7. Reload Configuration
    if ADDON.getSetting('MaintenanceReloadConfig{}'.format(schedule_id)) == 'true':
        log('Running config reloader for Schedule {}'.format(schedule_id))
        if show_notification:
            notify('Reloading configuration...')
        
        reloader_script = os.path.join(ADDON_PATH, 'resources', 'lib', 'config_reloader.py')
        if os.path.exists(reloader_script):
            xbmc.executebuiltin('RunScript({})'.format(reloader_script))
            xbmc.sleep(2000)  # Give it a moment to start
            tasks_completed.append('Config Reloaded')
    
    # 8. Force Channel Reset (Last)
    if ADDON.getSetting('MaintenanceForceReset{}'.format(schedule_id)) == 'true':
        log('Setting force channel reset for Schedule {}'.format(schedule_id))
        ADDON.setSetting('ForceChannelReset', 'true')
        tasks_completed.append('Channel Reset')
    
    # Log completion
    if tasks_completed:
        log('Maintenance completed. Tasks run: {}'.format(', '.join(tasks_completed)))
        if show_notification:
            notify('Maintenance completed: {}'.format(', '.join(tasks_completed[:3])))  # Show first 3
    else:
        log('No maintenance tasks were enabled for Schedule {}'.format(schedule_id))
        if show_notification:
            notify('No tasks enabled', 'Warning')
    
    # Update last run time
    import datetime
    now = datetime.datetime.now()
    ADDON.setSetting('LastMaintenanceRun{}'.format(schedule_id), now.strftime('%Y-%m-%d %H:%M'))

# Get the schedule ID from command line argument
if __name__ == "__main__":
    if len(sys.argv) > 1:
        schedule_id = sys.argv[1]
        execute_maintenance(schedule_id)
    else:
        log('No schedule ID provided', xbmc.LOGERROR)