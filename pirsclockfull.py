#! /usr/bin/env python
# -*- coding: utf-8 -*-
import pygame , sys , math, time, os, signal, subprocess
import RPi.GPIO as GPIO
from pygame.locals import *

def handle_sigterm(signum, frame):
    pygame.quit()
    GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)
os.environ["SDL_VIDEODRIVER"] = "kmsdrm"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Setting up the GPIO and inputs with pull up
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(12, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(13, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(15, GPIO.IN, GPIO.PUD_UP)

pygame.init()
bg = pygame.display.set_mode()
screen = pygame.display.set_mode((1280, 720), pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE)
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 100)
pygame.mouse.set_visible(False)

# Display modes
DISPLAY_CLOCK1 = 0
DISPLAY_CLOCK2 = 1
DISPLAY_BOTH = 2
current_display_mode = DISPLAY_CLOCK1

# Font mode toggle
use_custom_font = False  # True for clkfont, False for None

# Keyboard indicator states (for keys 1-4)
keyboard_indicators = {
    1: False,  # Key 1 state
    2: False,  # Key 2 state
    3: False,  # Key 3 state
    4: False   # Key 4 state
}

# Default colors (R,G,B) 255 max value
bgcolour       = (0,   0,   0  )
bgwhite        = (255, 255, 255)
# Clock and dot colors will be loaded from config.txt
default_clock_color = (255, 0, 0)    # Red
default_dot_color = (255, 255, 255)  # White
clockcolour    = default_dot_color    # Will be updated from config.txt
digitclockcolour = default_clock_color  # Will be updated from config.txt
offcolour      = (16,  16,  16 )
red            = (255, 0,  0   )
white          = (255, 255, 255)
green          = (0,   255, 0  )

# Function to load setup from external file
def load_setup():
    """Load indicator settings and clock colors from config.txt"""
    indicators = {}
    clock_colors = {
        'clock': default_clock_color,
        'dot': default_dot_color
    }
    
    default_settings = {
        'index1': ('ONAIR', (255, 255, 255), (255, 0, 0)),
        'index2': ('CUE', (255, 255, 255), (255, 255, 0)),
        'index3': ('STDBY', (255, 255, 255), (0, 255, 0)),
        'index4': ('REC', (255, 0, 0), (255, 255, 255))
    }

    try:
        with open(os.path.join(SCRIPT_DIR, 'config.txt'), 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Parse indicator lines (first 4 lines)
        for i, line in enumerate(lines[:4], 1):  # Read first 4 lines for index1-4
            line = line.strip()
            if not line:
                continue

            try:
                parts = line.split(',')
                if len(parts) >= 7:
                    text = parts[0]
                    text_r, text_g, text_b = int(parts[1]), int(parts[2]), int(parts[3])
                    bg_r, bg_g, bg_b = int(parts[4]), int(parts[5]), int(parts[6])

                    indicators[f'index{i}'] = (text, (text_r, text_g, text_b), (bg_r, bg_g, bg_b))
                else:
                    # Use default if format is incorrect
                    indicators[f'index{i}'] = default_settings[f'index{i}']
            except (ValueError, IndexError):
                # Use default if parsing fails
                indicators[f'index{i}'] = default_settings[f'index{i}']

        # Parse clock colors (5th line)
        if len(lines) >= 5:
            clock_line = lines[4].strip()
            if clock_line:
                try:
                    parts = clock_line.split(',')
                    if len(parts) >= 6:
                        clock_r, clock_g, clock_b = int(parts[0]), int(parts[1]), int(parts[2])
                        dot_r, dot_g, dot_b = int(parts[3]), int(parts[4]), int(parts[5])
                        
                        clock_colors['clock'] = (clock_r, clock_g, clock_b)
                        clock_colors['dot'] = (dot_r, dot_g, dot_b)
                except (ValueError, IndexError):
                    print("Error parsing clock colors, using defaults")

    except FileNotFoundError:
        print("config.txt not found, using default settings")
        indicators = default_settings
    except Exception as e:
        print(f"Error reading config.txt: {e}, using default settings")
        indicators = default_settings

    # Fill in any missing indicators with defaults
    for key in default_settings:
        if key not in indicators:
            indicators[key] = default_settings[key]

    return indicators, clock_colors

# Load settings from file
indicator_settings, clock_colors = load_setup()

# Update global clock colors
clockcolour = clock_colors['dot']
digitclockcolour = clock_colors['clock']

# Extract indicator settings
index1, ind1_text_color, ind1_bg_color = indicator_settings['index1']
index2, ind2_text_color, ind2_bg_color = indicator_settings['index2']
index3, ind3_text_color, ind3_bg_color = indicator_settings['index3']
index4, ind4_text_color, ind4_bg_color = indicator_settings['index4']

# Function to update font settings
def update_font_settings():
    global digiclocksize, digiclockspace, clockfont, current_digitclockcolour
    
    if use_custom_font and os.path.isfile(clkfont):
        # clkfont mode
        digiclocksize = int(bg.get_height()/8)
        digiclockspace = int(bg.get_height()/21)
        clockfont = pygame.font.Font(clkfont, digiclocksize)
    else:
        # None mode (system font)
        digiclocksize = int(bg.get_height()/4)
        digiclockspace = int(bg.get_height()/10.5)
        clockfont = pygame.font.Font(None, digiclocksize)
    
    # Always use the clock color from config.txt regardless of font type
    current_digitclockcolour = digitclockcolour

# Initial font and size setup
# Custom fonts (place in Fonts/ subdirectory to use with 'F' key toggle)
clkfont = os.path.join(SCRIPT_DIR, "Fonts", "DSEG7Classic-Regular.ttf")
indfont_path = os.path.join(SCRIPT_DIR, "Fonts", "GenShinGothic-P-Bold.ttf")

# Initialize font settings
current_digitclockcolour = digitclockcolour  # Initialize current color
update_font_settings()

# Other scaling values
dotsize        = int(bg.get_height()/90)
hradius        = bg.get_height()/2.5
secradius      = hradius - (bg.get_height()/26)
indtxtsize     = int(bg.get_height()/6)
indboxy        = int(bg.get_height()/6)
indboxx        = int(bg.get_width()/2.5)

# Coords of items on display
xclockpos      = int(bg.get_width()*0.2875)
ycenter        = int(bg.get_height()/2)
xtxtpos        = int(bg.get_width()*0.75)
xindboxpos     = int(xtxtpos-(indboxx/2))
ind1y          = int((ycenter*0.4)-(indboxy/2))
ind2y          = int((ycenter*0.8)-(indboxy/2))
ind3y          = int((ycenter*1.2)-(indboxy/2))
ind4y          = int((ycenter*1.6)-(indboxy/2))
txthmy         = int(ycenter)
txtsecy        = int(ycenter+digiclockspace)

# Initialize indicator font
if os.path.isfile(indfont_path):
    indfont = pygame.font.Font(indfont_path, indtxtsize)
else:
    indfont = pygame.font.Font(None, indtxtsize)

# Indicator text - now loaded from config.txt
ind1txt       = indfont.render(index1,True,bgcolour)
ind1txtactive = indfont.render(index1,True,ind1_text_color)
ind2txt       = indfont.render(index2,True,bgcolour)
ind2txtactive = indfont.render(index2,True,ind2_text_color)
ind3txt       = indfont.render(index3,True,bgcolour)
ind3txtactive = indfont.render(index3,True,ind3_text_color)
ind4txt       = indfont.render(index4,True,bgcolour)
ind4txtactive = indfont.render(index4,True,ind4_text_color)

# Indicator positions
txtposind1 = ind1txt.get_rect(centerx=xtxtpos,centery=ycenter*0.4)
txtposind2 = ind2txt.get_rect(centerx=xtxtpos,centery=ycenter*0.8)
txtposind3 = ind3txt.get_rect(centerx=xtxtpos,centery=ycenter*1.2)
txtposind4 = ind4txt.get_rect(centerx=xtxtpos,centery=ycenter*1.6)

# Function to toggle font
def toggle_font():
    global use_custom_font, txtsecy
    use_custom_font = not use_custom_font
    update_font_settings()
    # Update txtsecy position for second line
    txtsecy = int(ycenter + digiclockspace)

# Function to reload configuration
def reload_configuration():
    """Reload configuration from config.txt and update colors"""
    global indicator_settings, clock_colors, clockcolour, digitclockcolour
    global index1, ind1_text_color, ind1_bg_color
    global index2, ind2_text_color, ind2_bg_color
    global index3, ind3_text_color, ind3_bg_color
    global index4, ind4_text_color, ind4_bg_color
    global ind1txt, ind1txtactive, ind2txt, ind2txtactive
    global ind3txt, ind3txtactive, ind4txt, ind4txtactive
    global current_digitclockcolour
    
    try:
        # Reload settings
        indicator_settings, clock_colors = load_setup()
        
        # Update global clock colors
        clockcolour = clock_colors['dot']
        digitclockcolour = clock_colors['clock']
        
        # Extract indicator settings
        index1, ind1_text_color, ind1_bg_color = indicator_settings['index1']
        index2, ind2_text_color, ind2_bg_color = indicator_settings['index2']
        index3, ind3_text_color, ind3_bg_color = indicator_settings['index3']
        index4, ind4_text_color, ind4_bg_color = indicator_settings['index4']
        
        # Recreate indicator text objects
        ind1txt       = indfont.render(index1,True,bgcolour)
        ind1txtactive = indfont.render(index1,True,ind1_text_color)
        ind2txt       = indfont.render(index2,True,bgcolour)
        ind2txtactive = indfont.render(index2,True,ind2_text_color)
        ind3txt       = indfont.render(index3,True,bgcolour)
        ind3txtactive = indfont.render(index3,True,ind3_text_color)
        ind4txt       = indfont.render(index4,True,bgcolour)
        ind4txtactive = indfont.render(index4,True,ind4_text_color)
        
        # Update font settings to reflect new clock color
        update_font_settings()
        
        print("Configuration reloaded successfully")
        
    except Exception as e:
        print(f"Error reloading configuration: {e}")

# Function to check if indicator should be active
def is_indicator_active(gpio_pin, keyboard_key):
    """Check if indicator should be active based on GPIO or keyboard input"""
    gpio_active = not GPIO.input(gpio_pin)  # GPIO is active when LOW (inverted)
    keyboard_active = keyboard_indicators[keyboard_key]
    return gpio_active or keyboard_active

# Parametric Equations of a Circle to get the markers
# 90 Degree ofset to start at 0 seconds marker
# Equation for second markers
def paraeqsmx(smx):
    return xclockpos-(int(secradius*(math.cos(math.radians((smx)+90)))))

def paraeqsmy(smy):
    return ycenter-(int(secradius*(math.sin(math.radians((smy)+90)))))

# Equations for hour markers
def paraeqshx(shx):
    return xclockpos-(int(hradius*(math.cos(math.radians((shx)+90)))))

def paraeqshy(shy):
    return ycenter-(int(hradius*(math.sin(math.radians((shy)+90)))))

def get_clock1_time():
    """Get time for clock 1 (current implementation)"""
    return time.localtime(time.time())

def get_clock2_time():
    """Get time for clock 2 (placeholder - same as clock 1 for now)"""
    # TODO: This will be modified later for different functionality
    return time.localtime(time.time())

def draw_indicators():
    """Draw GPIO indicators with colors from config.txt"""
    # Indicator 1 (GPIO 11 or Key 1)
    if is_indicator_active(11, 1):
        pygame.draw.rect(bg, ind1_bg_color,(xindboxpos, ind1y, indboxx, indboxy))
        bg.blit(ind1txtactive, txtposind1)
    else:
        pygame.draw.rect(bg, offcolour,(xindboxpos, ind1y, indboxx, indboxy))
        bg.blit(ind1txt, txtposind1)

    # Indicator 2 (GPIO 12 or Key 2)
    if is_indicator_active(12, 2):
        pygame.draw.rect(bg, ind2_bg_color,(xindboxpos, ind2y, indboxx, indboxy))
        bg.blit(ind2txtactive, txtposind2)
    else:
        pygame.draw.rect(bg, offcolour,(xindboxpos, ind2y, indboxx, indboxy))
        bg.blit(ind2txt, txtposind2)

    # Indicator 3 (GPIO 13 or Key 3)
    if is_indicator_active(13, 3):
        pygame.draw.rect(bg, ind3_bg_color,(xindboxpos, ind3y, indboxx, indboxy))
        bg.blit(ind3txtactive, txtposind3)
    else:
        pygame.draw.rect(bg, offcolour,(xindboxpos, ind3y, indboxx, indboxy))
        bg.blit(ind3txt, txtposind3)

    # Indicator 4 (GPIO 15 or Key 4)
    if is_indicator_active(15, 4):
        pygame.draw.rect(bg, ind4_bg_color,(xindboxpos, ind4y, indboxx, indboxy))
        bg.blit(ind4txtactive, txtposind4)
    else:
        pygame.draw.rect(bg, offcolour,(xindboxpos, ind4y, indboxx, indboxy))
        bg.blit(ind4txt, txtposind4)

def draw_clock_markers(clock_time):
    """Draw second and hour markers using color from config.txt"""
    # Retrieve seconds and turn them into integers
    sectime = int(time.strftime("%S", clock_time))

    # To get the dots in sync with the seconds
    secdeg  = (sectime+1)*6

    # Draw second markers using clockcolour (dot color from config.txt)
    smx=smy=0
    while smx < secdeg:
        pygame.draw.circle(bg, clockcolour, (paraeqsmx(smx),paraeqsmy(smy)),dotsize)
        smy += 6  # 6 Degrees per second
        smx += 6

    # Draw hour markers using clockcolour (dot color from config.txt)
    shx=shy=0
    while shx < 360:
        pygame.draw.circle(bg, clockcolour, (paraeqshx(shx),paraeqshy(shy)),dotsize)
        shy += 30  # 30 Degrees per hour
        shx += 30

def draw_single_clock(clock_time):
    """Draw single clock display"""
    draw_clock_markers(clock_time)

    # Retrieve time for digital clock
    retrievehm    = time.strftime("%H:%M:%S", clock_time)
    retrievesec   = time.strftime("%S", clock_time)

    digiclockhm   = clockfont.render(retrievehm,True,current_digitclockcolour)
    digiclocksec  = clockfont.render(retrievesec,True,current_digitclockcolour)

    # Align it
    txtposhm      = digiclockhm.get_rect(centerx=xclockpos,centery=txthmy)
    txtpossec     = digiclocksec.get_rect(centerx=xclockpos,centery=txtsecy)

    # Render the text
    bg.blit(digiclockhm, txtposhm)

    draw_indicators()

def draw_dual_clock(clock1_time, clock2_time):
    """Draw both clocks in dual mode - only time display is duplicated"""
    # Use clock1 for markers
    draw_clock_markers(clock1_time)

    # Determine offset based on font type
    if use_custom_font:
        # Custom font: use 0.6 offset
        offset_multiplier = 0.6
    else:
        # System font (None): use 0.3 offset
        offset_multiplier = 0.3

    # Dual time display positions
    dual_time_y1 = int(ycenter - digiclocksize * offset_multiplier)  # Upper time
    dual_time_y2 = int(ycenter + digiclocksize * offset_multiplier)  # Lower time

    # Retrieve time for both clocks
    retrievehm1   = time.strftime("%H:%M:%S", clock1_time)
    retrievehm2   = time.strftime("%H:%M:%S", clock2_time)

    # 同じフォントサイズを使用
    digiclock1hm  = clockfont.render(retrievehm1,True,current_digitclockcolour)
    digiclock2hm  = clockfont.render(retrievehm2,True,current_digitclockcolour)

    # Align them
    txtpos1hm     = digiclock1hm.get_rect(centerx=xclockpos,centery=dual_time_y1)
    txtpos2hm     = digiclock2hm.get_rect(centerx=xclockpos,centery=dual_time_y2)

    # Render the text
    bg.blit(digiclock1hm, txtpos1hm)
    bg.blit(digiclock2hm, txtpos2hm)

    draw_indicators()

def toggle_display_mode():
    """Toggle between display modes"""
    global current_display_mode
    current_display_mode = (current_display_mode + 1) % 3

# IP address display
show_ip = False
ip_font = pygame.font.Font(None, int(bg.get_height()/20))
ip_margin = 10

def get_ip_addresses():
    """Get IP addresses for all active network interfaces"""
    addrs = []
    try:
        result = subprocess.run(
            ['hostname', '-I'], capture_output=True, text=True, timeout=2
        )
        for addr in result.stdout.strip().split():
            if '.' in addr:  # IPv4 only
                addrs.append(addr)
    except Exception:
        pass
    return addrs[:2]  # max 2 lines

def draw_ip_addresses():
    """Draw IP addresses at bottom-right of screen"""
    addrs = get_ip_addresses()
    if not addrs:
        addrs = ['No IP']
    screen_w = bg.get_width()
    screen_h = bg.get_height()
    y = screen_h - ip_margin
    for addr in reversed(addrs):
        rendered = ip_font.render(addr, True, white)
        rect = rendered.get_rect(right=screen_w - ip_margin, bottom=y)
        bg.blit(rendered, rect)
        y = rect.top - 2

# Configuration reload timer (check every 5 seconds)
last_config_check = time.time()
CONFIG_CHECK_INTERVAL = 5.0

# This is where pygame does its tricks
while True :
    pygame.display.update()

    bg.fill(bgcolour)

    # Check for configuration reload periodically
    current_time = time.time()
    if current_time - last_config_check > CONFIG_CHECK_INTERVAL:
        try:
            # Check if config.txt has been modified
            stat_info = os.stat(os.path.join(SCRIPT_DIR, 'config.txt'))
            if not hasattr(reload_configuration, 'last_mtime'):
                reload_configuration.last_mtime = stat_info.st_mtime
            elif stat_info.st_mtime > reload_configuration.last_mtime:
                print("config.txt modified, reloading configuration...")
                reload_configuration()
                reload_configuration.last_mtime = stat_info.st_mtime
        except:
            pass  # Ignore errors checking file modification time
        
        last_config_check = current_time

    # Get times for both clocks
    clock1_time = get_clock1_time()
    clock2_time = get_clock2_time()

    # Draw based on current display mode
    if current_display_mode == DISPLAY_CLOCK1:
        draw_single_clock(clock1_time)
    elif current_display_mode == DISPLAY_CLOCK2:
        draw_single_clock(clock2_time)
    elif current_display_mode == DISPLAY_BOTH:
        draw_dual_clock(clock1_time, clock2_time)

    # Draw IP addresses if enabled
    if show_ip:
        draw_ip_addresses()

    # Check currently pressed keys for momentary control
    keys = pygame.key.get_pressed()
    keyboard_indicators[1] = keys[K_1]
    keyboard_indicators[2] = keys[K_2]
    keyboard_indicators[3] = keys[K_3]
    keyboard_indicators[4] = keys[K_4]

    #time.sleep(0.04)
    pygame.time.Clock().tick(0)
    for event in pygame.event.get() :
        if event.type == QUIT:
            pygame.quit()
            GPIO.cleanup()
            sys.exit()
        elif event.type == KEYDOWN:
            if event.key == K_q:
                pygame.quit()
                GPIO.cleanup()
                sys.exit()
            # elif event.key == K_SPACE:
            #     toggle_display_mode()
            elif event.key == K_f:
                toggle_font()
            elif event.key == K_a:
                show_ip = not show_ip
            elif event.key == K_r:
                # Manual reload configuration with 'R' key
                print("Manual configuration reload requested...")
                reload_configuration()
