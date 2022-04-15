"""
Simple image tab downloader for chan.sankakucomplex.com using a different approach
Developed since widely available image grabbing softwares
have been defeated by erroneous loading employed by Sankaku
to block batch downloaders.

Compatible with Firefox only with dark mode settings

@author Jeff Chen
@created 4/5/2022
@version 0.2

Changelog: 0.2
- Converted project to use Selinium for huge performance boost
- Added initiator for selinium using custom Firefox profile
- Automatic scrolling for image link harvesting
- Improved tab opening (Extract links directly instead of manual clicking)
- Added multiple flags, including demo and debug modes
- Slowdown/error screen detection and resolution detection

"""
import profile
import time
from cv2 import CALIB_CB_FAST_CHECK
import keyboard
import pyautogui as pg
import os
import mouse
import numpy as np
import sys
from selenium.webdriver import Firefox
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import cv2
import urllib


# Preliminaries
######################## cd to icon directory ########################
def setDir():
    os.chdir("..")
    os.chdir("icons")
    #TODO - check file contents

################### Determine the leftmost border ###################
def getBorder():
    icon = pg.locateOnScreen('lborder.png', confidence=0.99)
    if icon == None:
        print("Unable to pickup leftmost border, please adjust confidence or switch to correct window")
        exit()
    return icon[0]       # leftmost border of clickable content

####################### End of Preliminaries #########################

### Misc variables
BORDER_COLOR = [27,27,27]       # Color of image border
ERROR_COLOR = [255,255,255]     # Border color of Sankaku error page
WAIT_COLOR = [250,250,250]      # Border color of Sankaku please wait page
IMAGE_DIFFERENCE = 420          # Pixel difference from center of one image to next image
NEXT_ROW = 3.5                  # Scrolls to move to next row of images
NEXT_GRID = 5.3                 # Scrolls needed to move to next grid of images
SCROLL_BUFFER = 0.5             # Seconds to wait for scrolling
CURSOR_MOVE_BUFFER = 0.1        # Seconds to wait for cursor movement
CENTER_TOLERANCE = 35           # Pixel steps to find center point, incresing value increases speed, decreasing value too much or big results in bugs
WINSIZE = [3840,2160]           # Size of Firefox Window
PROFILE_PATH = r'C:/Users/chenj/AppData/Roaming/Mozilla/Firefox/Profiles/8gtgo2sw.default-release'  # Path of Firefox custom profile
lastScreenSize = None           # Last recorded Firefox resolution (used to optimize out duplicate calculations)
savedTopBorder = None           # Used to optimize out duplicate calculations
debug = False                   # Debugger switch, true for additional output, false for normal output
demo = False                    # True for demo mode, false for not
clicks = 0                      # DEPRECATED
windowsRes = None               # Resolution of Windows resolution (screen resolution)
ffToWinRatio = None             # Ratio of Selinium firefox browser to Windows resolution
folder = '/home/palladin/imgs'  # Download directory

def getRatio(c1:int, c2:int)->float:
    """
    Solve c1*x=c2 for x
    Pre: c1 != 0
    Param: 
        c1: c1 in c1*x=c2
        c2: c2 in c1*x=c2
    Return: x in c1*x=c2
    """
    return c2/c1
    
def resolution_autodetect(driver:Firefox)->None:
    """
    Detects screen and full screen Selinium firefox resolution and calculates firefox resolution
    to screen ratio. 
    Params:
        driver: Selinium Firefox driver
    Post: globals windowRes, ffToWinRatio, lastScreenSize updated
    """
    global windowsRes
    global ffToWinRatio
    global lastScreenSize
    print("Detecting resolutions, do not modify firefox window size...")
    driver.maximize_window()        # Make full screen
    time.sleep(0.5)
    windowsRes = pg.size()          # Get screen resolution 
    lastScreenSize = getWindowSize(driver)
    ffToWinRatio = [getRatio(lastScreenSize["width"], windowsRes[0]), getRatio(lastScreenSize["height"], windowsRes[1])]
    print("Resolution detection completed:")
    print("Screen resolution: ", windowsRes)
    print("Firefox resolution: ", lastScreenSize)
    print("Firefox to screen ratio: ", ffToWinRatio)
    print("Converted Firefox to screen resolution (Must be almost equal to Screen Resolution): ", lastScreenSize["width"]*ffToWinRatio[0], ", ", lastScreenSize["height"]*ffToWinRatio[1])

def selinium_slowdown_detector(driver:Firefox)->None:
    """
    Detects if a page contains a Sankaku error or slowdown using pixel arithmetic. If detected,
    page will be refreshed until message is no longer detected.
    Params: 
        driver: Selinium Firefox driver
    Post: page no longer contains a Sankaku error or slowdown
    """
    global lastScreenSize
    global topBorder
    global ffToWinRatio
    global windowsRes
    if(np.array_equal(getWindowSize(driver), lastScreenSize) == False or topBorder == None):
        # Detect current FF size
        lastScreenSize = getWindowSize(driver)

        # Get FF position
        curr = driver.get_window_position()

        # Get Inner FF dimensions
        innerHeight = driver.execute_script("return window.innerHeight;")
        innerWidth = driver.execute_script("return window.innerWidth;")

        # Get offset (distance from FF window to inner window)
        xoffset = lastScreenSize["width"] - innerWidth
        yoffset = lastScreenSize["height"] - innerHeight
        
        # Get Top right coordinate of FF inner window
        topBorder = [(curr["x"] + lastScreenSize["width"] - xoffset) * ffToWinRatio[0], (curr["y"] + yoffset) * ffToWinRatio[1]]

        if(debug == True):
            print("\nREAL SIZE:\t", windowsRes)
            print("FIREFOX SIZE:\t", lastScreenSize) # 1900, 2000
            print("CONVERTED FF SIZE:\t", lastScreenSize["width"]*ffToWinRatio[0], ", ", lastScreenSize["height"]*ffToWinRatio[1])
            print("INNER FF WINDOW:\t", innerWidth, ", ", innerHeight)
            print("CONVERTED INNER FF: ", innerWidth * ffToWinRatio[0], ", ", innerHeight * ffToWinRatio[1])
            print("OFFSETS: X = ", xoffset, ", y = ", yoffset)
            print("CURRENT FF POSITION: ", curr)
            print("RATIO FF TO REAL: ", ffToWinRatio)
            print("NEW FF POSITION:\t", topBorder, flush=True)
            print("\nMOUSE MOVED TO NEW FF POSITION, CURSOR SHOULD BE TOP RIGHT CORNER BELOW BOOKMARK BAR")
            mouse.move(topBorder[0], topBorder[1], True)
    
    elif debug == True :
        print("\nOPTIMIZING OUT CALCULATIONS")
        mouse.move(topBorder[0], topBorder[1], True)
    
    # Processing pixel check for slowdown/error message
    color = pg.pixel(int(topBorder[0]), int(topBorder[1]))
    if(np.array_equal(color, ERROR_COLOR) or np.array_equal(color, WAIT_COLOR)):
        print("Error detected, refreshing page")
        driver.refresh()
        

def selinium_save_image(driver:Firefox)->None:
    r=driver.find_elements_by_tag_name('img')
    src = r.get_attribute("src")
    pos = len(src) - src[::-1].index('/')
    print (src[pos:])
    g=urllib.urlretrieve(src, "/".join([folder, src[pos:]]))

def getWindowSize(driver:Firefox)->dict:
    """
    Returns the current Firefox Window size

    Params:
        driver - selinium driver which has already been opened to Firefox
    
    Pre:
        Selinium window is still open.
    """
    return driver.get_window_size()

def selenium_infscroll(driver:Firefox)->None:
    """
    Scrolls to the end of the selenium window
    DEBUG: prints old scroll height vs new scroll height
    """
    SCROLL_PAUSE_TIME = 2
    html = driver.find_element_by_tag_name('html')

    # Get scroll height
    last_height = driver.execute_script("return window.pageYOffset + window.innerHeight")


    while True:
        # Scroll down to bottom
        html.send_keys(Keys.PAGE_DOWN)
        html.send_keys(Keys.PAGE_DOWN)
        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return window.pageYOffset + window.innerHeight")
        if(debug == True):
            print("OLD: ", last_height, "\tNEW: ", new_height, flush=True)
        if new_height == last_height:
            break
        last_height = new_height

    time.sleep(SCROLL_PAUSE_TIME)
    print("Scrolling completed")

def selenium_init()->Firefox:
    """
    Initializes and opens a selinium Firefox window with custom profile path PROFILE_PATH
    """
    opt=Options()
    opt.add_argument("-profile")
    opt.add_argument(PROFILE_PATH)
    driver = webdriver.Firefox(options=opt)
    return driver

def selenium_visit(driver:Firefox)->None:
    """
    Opens all content urls from https://chan.sankakucomplex.com in another tab

    Pre: On page on sankakucomplex
    Post: All content urls opened in another tab, original tab returned to
    BUGS: issue where js scripts ran using Tampermonkey extension fail to activate on home page of sankakucomplex
    """
    cont = True

    while(cont == True):
        print("Type the sankaku url you want to visit:")
        url = input("URL> ")
        
        if("chan.sankakucomplex.com" not in url):
            print("You did not enter a valid link, links contain https://chan.sankakucomplex.com")
        else:
            driver.get(url)
            selenium_infscroll(driver)
            time.sleep(0.5)
            if demo == False:
                p = driver.current_window_handle()
                for a in driver.find_elements(by=By.XPATH, value='.//a'):
                    if("https://chan.sankakucomplex.com/post/show/" in a.get_attribute('href')):
                        print("Opening: ", a.get_attribute('href'))
                        driver.execute_script('window.open("{}","_blank");'.format(a.get_attribute('href')))
                        time.sleep(0.5)
                driver.switch_to.window(p)  
            cont = False
    
    print("All tabs opened")

def selenium_download(driver:Firefox)->None:
    """
    Downloads image 
    """
    # Preliminaries
    LOADING_BUFFER = 2
    TAB_BUFFER = 0.1

    # Iterate until return to original url
    orig_url = driver.current_url()

    # Switch the next tab by closing current tab
    driver.findElement(By.cssSelector("body")).sendKeys(Keys.CONTROL, Keys.PAGE_DOWN)


    while(orig_url != driver.current_url()):
        kill_switch()

        icon = pg.locateOnScreen('slowdown_msg.png')
        slowdown_detector()

        # Keep looping as long as slowdown msg exists
        while(icon != None):
            warning_detector()

            # Check if is a slowdown window
            if(icon != None):
                
                icon = pg.locateOnScreen('refresh_icon.png')

                # Attempt refresh if found
                if(icon != None):
                    x = icon[0] + icon[2]/2
                    y = icon[1] + icon[3]/2
                    mouse.move(x, y, True, 0)
                    mouse.click()
                    loading_detector()


            # Take another screenshot and check if msg still exists
            icon = pg.locateOnScreen('slowdown_msg.png')

        # Process image by drag drop
        mouse.drag(430, 587, 2800, 552, True, 0.1)
        warning_detector()
        moving_detector()

        # Close current window
        mouse.move(1,1,True)
        mouse.click()
        pg.keyDown("ctrl")
        pg.press("w")
        pg.keyUp("ctrl")

        kill_switch()

        # Wait for window to load
        loading_detector()
            
        icon = pg.locateOnScreen('terminate_icon.png', confidence=0.5)


    # escape condition
    cv2.waitKey(0)

    # clean up windows
    cv2.destroyAllWindows()

    print("Program terminating on completion")

def main():
    global debug
    global demo

    # argv
    if(len(sys.argv) > 1):
        if(sys.argv[1][0] == '-'):
            if("-d" == sys.argv[1]):
                print("Demo mode has been selected. Images will not be opened but other interactions will still be enabled")
                demo = True
            elif("-DBUG_CTR" == sys.argv[1]):
                debug = True
                print("RUNNING 1 ITERATION OF CENTER_CURSOR")
                center_cursor()
                print("DBUG COMPLETED")
                exit()
            elif("-DBUG_WINSZ" == sys.argv[1]):
                print("CHECKING FIREFOX WINDOW SIZE")
                driver = selenium_init()
                print(getWindowSize(driver))
                print("DBUG COMPLETED")
                driver.quit()
                exit()
            elif("-DBUG_WIN" == sys.argv[1]):
                print("OPENING SELINIUM WINDOW WITH CUSTOM PROFILE AT: ", PROFILE_PATH)
                selenium_init()
                print("DBUG COMPLETED")
                exit()
            elif("-DBUG_SEARCHWIN" == sys.argv[1]):
                print("SEARCHING IN SELINIUM WINDOW WITH CUSTOM PROFILE")
                demo = True
                debug = True
                driver  = selenium_init()
                selenium_visit(driver)

                while(input("Continue? y or n>") != 'n'):
                    selenium_visit(driver)
                print("DBUG COMPLETED")
                driver.quit()
                exit()
            elif("-DBUG_SAVE" == sys.argv[1]):
                demo = True
                debug = True
                print("TESTING SAVING")
                driver = selenium_init()
                resolution_autodetect(driver)
                while(input("Detect? y or n>") != 'n'):
                    selinium_slowdown_detector(driver)
                    selinium_save_image(driver)
                driver.quit()
                exit()
            else:
                print("\nInvocation: python ImageOpenor.py <switch>")
                print("\nSwitches")
                print("-h           Help")
                print("-d           Demo mode")
                print("\n\nDebug switches:\n-DBUG_CTR    Tests center cursor")
                print("-DBUG_WINSZ  Get current selinium Firefox window size")
                print("-DBUG_WIN    Open a selinium Firefox window with custom profile settings")
                print("DBUG_SEARCHWIN   Open a selinium Firefox with website searching and prep in demo mode")
                exit()
                


    rows = 0    # counter of  number of rows processed
    setDir()    # set relative directory to icons
    lborder = getBorder()   # get leftmost border of content

    print("While program is in progress, DO NOT MOVE YOUR CURSOR")
    print("Hold ESC on your keyboard to terminate", flush=True)

    if keyboard.is_pressed("Esc"):
        exit()


    terminate = pg.locateOnScreen('terminate_icon.png', confidence=0.3)

    # Keeps running until termination icon is visable
    while True:

        opos = pg.position()   
        processRow(lborder, demo)
        rows = rows + 1
        #mouse.click("middle")
        mouse.move(opos[0], opos[1], True)

        
        # For incrementing to next grid segment
        mouse.wheel(NEXT_ROW)
        time.sleep(SCROLL_BUFFER)

        # Increment into next grid if needed
        if np.array_equal(pg.pixel(pg.position()[0], pg.position()[1]), BORDER_COLOR):
            mouse.wheel(NEXT_GRID)
            time.sleep(SCROLL_BUFFER)

        # Process last row on screen once terminate icon is spotted
        terminate = pg.locateOnScreen('terminate_icon.png', confidence=0.4)
        if(terminate != None):
            if(rows != 1):
                processRow(lborder)
                rows = rows + 1
            break               # Hate using break but need do-while loop not available in python

    print("Terminating on termination logo, CLICKS: ", clicks, " Rows: ", rows)

######################## DEPRECATED/UNUSED ########################
def moving_detector():
    """
    Unused for now
    Scans the screen to see if an image is in progress of moving, pauses program execution until image 
    has finished moving
    """
    time.sleep(0.5)
    icon = pg.locateOnScreen('~/icons/moving_icon.png', confidence=0.5)
    if icon != None:
        while(icon != None):
            print("moving detected, sleeping for 1 second...", flush=True)
            time.sleep(1)
            icon = pg.locateOnScreen('moving_icon.png', confidence=0.5)
        print("Program resuming", flush=True)
def kill_switch():
    """
    Unused for now
    End and destroy program when "esc" is pressed
    """
    if keyboard.is_pressed("Esc"):
        # escape condition
        cv2.waitKey(0)

        # clean up windows
        cv2.destroyAllWindows()

def warning_detector():
    """
    Unused for now
    Scans the screen to see if there is an image download conflict. If detected,
    program execution paused until ctrl is pressed
    """
    # Check for warning
    time.sleep(0.5)
    icon = pg.locateOnScreen('cancel_icon.png', confidence=0.5)
    if(icon != None):
        print("Warning detected, press and hold ctrl to continue", flush=True)
        while keyboard.is_pressed("ctrl") == False:
            time.sleep(1)
        print("Program resuming", flush=True)

def loading_detector():
    """
    Unused for now
    Scan the screen to detect if the current page is loading. Sleep until page has loaded
    """
    mouse.move(1,1, True)
    time.sleep(0.5)
    icon = pg.locateOnScreen('loading_icon.png', confidence=0.5)
    if icon != None:
        while(icon != None):
            print("loading detected, sleeping for 1 second...", flush=True)
            time.sleep(1)
            icon = pg.locateOnScreen('loading_icon.png', confidence=0.5)
        print("Program resuming", flush=True)

def processRow(lborder):
    """
    @DEPRECATED - replaced by selenium_visit()
    Processes a row of images by processing one image and then moving left
    until cursor is past the lborder

    If the cursor is on the border, it will not process the image but move 
    left until cursor is past the lborder

    args:
        - lborder: leftmost border of the leftmost content. 

    Pre: lborder is valid.

    Post: Single row of content processed, cursor will be at first location left of lborder

    Return Nothing
    """
    global clicks
    global demo

    # Processing grid segment
    while(lborder < pg.position()[0]):
        time.sleep(CURSOR_MOVE_BUFFER)
        # TODO - if statement for if on dead space

        if(demo == False):
            mouse.click("middle")
        clicks = clicks + 1
        pos = pg.position()
        mouse.move(pos["width"] - IMAGE_DIFFERENCE, pos["height"], True)
        time.sleep(SCROLL_BUFFER)
        if keyboard.is_pressed("Esc"):
            exit()

def center_cursor():
    """
    @DEPRECATED - replaced by selenium_visit()
    Centers the cursor to the content the cursor is on.

    Pre: cursor must be within a piece of content
    Post: cursor centered on piece of content
    
    """
    if np.array_equal(pg.pixel(pg.position()[0], pg.position()[1]), BORDER_COLOR):
        print("Please put your cursor within an piece of content, not on the border")
        exit()
    
    x = 0
    y = 0

    # Move to left-most, bottom-most corner
    while np.array_equal(pg.pixel(pg.position()[0], pg.position()[1]), BORDER_COLOR) != True:
        pg.move(-CENTER_TOLERANCE, 0)
    pg.move(CENTER_TOLERANCE,0)
    time.sleep(1)
    while np.array_equal(pg.pixel(pg.position()[0], pg.position()[1]), BORDER_COLOR) != True:
        pg.move(0, CENTER_TOLERANCE)
    pg.move(0, -CENTER_TOLERANCE)
    time.sleep(1)

    # Calculating x-center
    while np.array_equal(pg.pixel(pg.position()[0], pg.position()[1]), BORDER_COLOR) != True:
        pg.move(CENTER_TOLERANCE, 0)
        x = x - CENTER_TOLERANCE
    pg.move(-CENTER_TOLERANCE, 0)
    x = x + CENTER_TOLERANCE
    time.sleep(1)

    # Calculating y-center
    while np.array_equal(pg.pixel(pg.position()[0], pg.position()[1]), BORDER_COLOR) != True:
        pg.move(0, -CENTER_TOLERANCE)
        y = y + CENTER_TOLERANCE
    pg.move(0, CENTER_TOLERANCE)
    y = y - CENTER_TOLERANCE
    time.sleep(1)

    pg.move(x>>1, y>>1)

    global debug
    if(debug):
        print("XLEN: ", x)
        print("YLEN: ", y)
        print("MOVE FROM UPPER RIGHT CORNER: X + ", x>>1, ", Y + ", y>>1)
if __name__=="__main__":
    main()
