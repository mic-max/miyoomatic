# Miyoo-matic
Automating the button presses on a handheld console.
Play a Miyoo handheld console automatically with solenoids and a webcam.

## Requirements
1. [Python 3](https://www.python.org/downloads/)
1. [SQLite Tools](https://sqlite.org/download.html)
1. [Ardunio CLI](https://arduino.github.io/arduino-cli)
1. [OBS Studio](https://obsproject.com/download)
1. [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)

[FireRed ROM](https://vimm.net/vault/5626)

## PC First Time Setup
1. `sqlite3 -init pc/setup.sql miyoomatic.db .quit`
1. `python -m venv myenv`
1. `./venv/Scripts/Activate.ps1`
1. `pip install -r pc/src/requirements.txt`

## Subsequent Setup
1. `./venv/Scripts/Activate.ps1`
1. `ruff check`
1. `python pc/src/main.py`

## Arduino Setup
1. `arduino-cli config init`
1. `arduino-cli core update-index`
1. `arduino-cli core install arduino:avr`
1. `arduino-cli compile --fqbn arduino:avr:nano:cpu=atmega328old Serial`
1. `arduino-cli upload -p COM3 --fqbn arduino:avr:nano Serial`

## Extract Palette From ROM
- They are 16x 15-bit colors compressed with LZ10
- Pointers to all Pokemon palettes are stored in a single table. Its offset is located at 0x130
- Shiny palette pointer is at 0x134 - but it turns out we can use the "normal" address to locate those as well?????
pointers are 24 bit?
- palette pointers are ordered according to internal id number, which is the same as the pokedex number for gen1 and gen2 atleast
- 

## Fun Palette SQL Queries
- Pokemon that uses a single color the most/least, by percentage
- Most/least common colors
  - By number of palettes they are in
  - By total number of pixels
- Pokemon with the least/most amount of colors
- Group pokemon by their background color
- Pokemon that represent a single color with multiple palette colors
  - Used by some shiny pokemon to add a hidden element?


## Camera Settings
- Zoom: 10/10 - Zoom in as much as you can without cutting off any of the screen
- Brightness: 35/100 - I decreased this until the background looked completely dark
- Contrast: 50/100 - Unchanged
- Sharpness: 100/100 - Makes the edges of pixels much clearer
- Saturation: 50/100 - Unchanged
  - TODO: Increased to 75 to get closer to the look of the sprites

## Troubleshooting
- Image Too Bright: Open the Windows Camera app, then launch the Python program
- Image Too Zoomed: Open "Manage cameras" and select your camera, ensure focus and close lid and program, then try running again.
- Start the program in the overworld
  - This lets the program best detect the screen's border
- Image Detection Issues
  - Clean the webcam lens and the screen

## Testing
- Add unit tests

## Resources
<!-- TODO include all resourced I used to build this program and learning references used -->
- Font from cufonfonts. converted TTF to WOFF online
<!-- https://bulbapedia.bulbagarden.net/wiki/Celadon_Game_Corner#Generation_III_3 -->
- <https://pseudopencv.site/utilities/hsvcolormask/> So helpful when I was trying to figure out useful HSV mask ranges for gender detection.
- <https://voliol.neocities.org/articles/genIIIpalettes> How colour palettes work in Fire Red
- <https://pokemondb.net/tools/text-list> helped me fill my database

<!-- TODO: scale textures evenly by doubling and using proper scale up algo. -->

## Training
- Make training the image recognition model easy to do and update
- It only needs to classify items into 1 of 3 things or unknown, realistically

// TODO: Add setup commands for each script that only happen once to simplify prereqs or verify everything is prepared
    // TODO: this is giving the PC limited information about the screenshot.
    // if a script needs to take two different kinds then the PC will need to differentiate them somehow, maybe just have a few
    // like PrintScreen2, PrintScreen3, etc. and send a different byte over serial line.
    // Or better yet make the parameter 1,2,3, etc. instead of zero and send over another byte.

// TODO: Read button map from two 8 DIP switches?
// TODO: make the delay in terms of ticks? like 60 ticks per second multiples? with a small constant.
// start conditions:
//   floor 3 pokemon tower
//   menu closed but will hover pokemon if open
//   text speed is set to fast
//   have multiple ultra balls
//   PKMN #1
//   - sweet scent as first ability
//   - must be able to always run (speed >= 67 (Lv20 Haunter max speed TODO: verify this) OR hold smoke ball (diff timing?))
//   - else: have it fainted and next alive pokemon slot can always run
//   pokemon that is used in the encounter
//    - has single character nickname
//    - has a move that can sleep or freeze the gastly, near 100% catch rate with ultra ball.

// Note: doesn't work on ghost since it's a normal move.
//    - scyther with false swipe leaves opponent at 1HP, 100% catch rate with Great Ball

// TODO: maybe I can send a command to python saying I will take at least the sum of all the millseconds i
// delay for, so you can go ahead and sleep your thread for that long and then wake up and start checking 
// for a message every 10ms or so. so the main thread isn't taking up too much CPU time.
// TODO: NOOP command. would allow for easily commenting out commands from a script if not needed.
//       for example if im somewhere in the desert and it says the sun is beating or has a longer animation. I can comment something out
//       rather than changing the entire thing. id have to add to the original delay for example. and lose what the original delay value was.
//       or I could generate the script from a function that takes inputs like current weather event, etc.

// TODO: replace for loop with a variable for remembering the index and then just modulus that in my void loop.
// that lets me interrupt the flow of the program more to compute other things in between script actions.
// maybe I could use 7 seg display to show iterations
// show 

// TODO: Read a dip switch to select the script by index
// int catch[12][2] = {};

// start conditions:
//   have >= 50 coins
//   at a slot machine with no coins yet inserted
// Stop when i have >= 9900 coins (enough to buy 55 ABRAs)
// Note: ~150 complete buys to probably receive a shiny.
int slots[8][2] = {
  {       Down, 100}, // coin
  {       Down, 100}, // coin
  {       Down, 100}, // coin
  {          A, 100}, // pull
  {          A, 100}, // pull
  {          A, 100}, // pull
  // TODO: I think holding A fast forwards the coin payout... solenoids are not ideal for staying active though...
  {PrintScreen,  -1}, // over serial: tell PC to take a photo
  {       Wait,  -1}, // wait for a message over serial
  // The PC will check the screenshot for number of coins won and use that to determine additional wait time before sending a resume command over serial
  // Or should the PC reply with a byte that can be used by the arduino to determine how long to wait?
};

// TODO: Figure out how long an in-game step and a turn take and make those commands of their own eg. turnwalkup2, turnwalkup3, walkup1, walkup2, turnrunleft5, etc.
// TODO: perma-run? can i always hold run with a 3d printed thing? no solenoid on it?
// TODO: if i have an extra button outdoors maybe i can press select for my bike
// TODO: cat the scripts: slot machine script + walk to prize corner + walk to casino + buy abra

// Down, Left, Up, A
int walkToGameCorner[8][2] = {
  {Down, 1500}, // exit shop, turn + down 5 steps
  // Animation of door exit
  {Down,  200}, // down 1 step
  {Left, 1500}, // turn + left 5 steps
  {  Up,  200}, // turn + up 1 step
  // Animation of door enter
  // Note: I could choose to go 3 up and right but that requires a new button.
  {  Up, 1100}, // up 4 steps
  {Left, 1500}, // turn + left 2 steps
  {   A,  600}, // select slot machine
  {   A, 1300}, // yes to dialog
};

int walkToPrizeCorner[2][2] = {
  {B, 600}, // exit slot machine
  {A, 1200}, // confirm dialog
  // turn + right 2
  // turn + down 5
  // turn + right 5
  // turn + up 2
  // up 4
};

// TODO: make a function that takes a string, A-Z a-z space 0-9 !?/-./ quotation mark and apostrophe open and close, ellipsis, male, female 
// int giveNickname[][2] = {

// };

// start conditions
// have at least 55 spaces in your PC open
// make it so the pokemon is inserted in the empty boxes.
// TODO: make sure I dont run into any NPCs
int walkToPokemonCenter[1][2] = {
  {Down, 200}, // down 1 step
  // turn + right 4
  // turn + up 10
  // turn + right 5
  // turn + up 1
  // up 3
  // turn + right 4
  // turn + up 3
  // boot up PC
  // skip dialog
  // choose Bill's
  // skip dialog
  // skip dialog
  // down
  // down
  // select move pokemon
};

// Whatever current box i am in
// box is full of pokemon
// cursor located at top right
// if a shiny is in the box it will not be released and the arduino will be stuck waiting hovering that pokemon

// TODO: develop something to go to the next box, maybe part of the input can be the number of pokemon to check (55)
// TODO: have a function fill the data of this array since it will be hundreds of commands long.
int releaseNonShiny[][2] = {

};

  // now i can either just check the color of the sprite or an easier way would likely be to open the summary and check for the star or a blue border instead of purple
  // a, select pokemon
  // down to summary
  // click summary
  // screenshot
  // press A to exit summary
  // wait
  // if not shiny:
    // press a on pokemon
    // down 4 or up 2
    // press A on release
    // press up
    // press A
    // skip dialog (up arrow worked too)
    // skip dialog
  // end if
  // go right
  // if i != 0 and i % 5 == 0:
  //   go down
//};

// start conditions:
// - have at least 180 coins
// looking at a full box one to the left of the empty "RIP Abra" box
// "caught pokemon will be sent directly to the PC, to whichever box you last accessed"
// Note: buyClefairy, buyDratini, buyScyther and buyPorygon will all be very similar.
int buyAbra[7][2] = {
  {A, 500}, // talk
  {A, 100}, // skip dialog
  {A, 100}, // select abra
  {A, 100}, // buy abra
  {B, 100}, // skip nickname OR press down then A (useful if I can't spare a B button, but will be slightly slower)
  // {Down, 100},
  // {A, 100},
  {A, 100}, // skip abra being put in PC
  // NOTE: Once you have filled the currently hovered box there will be an additional dialog!
  {A, 100}, // skip dialog
  // TODO:
};


  # TODO: alternate loop style
  # while True:
  #     try:
  #         msg = incoming.get_nowait() # non-blocking
  #         print(msg)            
  #     except queue.Empty:
  #         pass


  #TODO read https://docs.python.org/3/library/queue.html implementation and how it works with threads
