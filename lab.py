import os
import sys
import random
import pygame
import math

# Class for the orange dude
class Player(object):
    
    def __init__(self):

        # Game map
        self.rect = pygame.Rect(32, 32, 16, 16)
        
        # Player movement
        self.move_angle     = random.uniform(-math.pi, math.pi) # Player will move into random direction at start
        self.shift_speed    = 0.1 # Degrees each left or right turn shifts the direction vector
        self.move_speed     = 0.2

    def shift_direction(self, current_angle, shift):
        # OUTPUT
        # Tuple (x, y)      directional vector in 2D
        self.move_angle     = current_angle + shift
        x                   = math.cos(self.move_angle)
        y                   = math.sin(self.move_angle)

        return (x, y)

    def move(self, dx, dy):
        
        # Move each axis separately. Note that this checks for collisions both times.
        self.move_single_axis(dx, 0)
        self.move_single_axis(0, dy)
    
    def move_single_axis(self, dx, dy):
        
        # Move the rect
        self.rect.x += dx
        self.rect.y += dy

        # If you collide with a wall, move out based on velocity
        for wall in walls:

            if pygame.Rect.colliderect(wall.rect, self.rect):
                if dx > 0: # Moving right; Hit the left side of the wall
                    self.rect.right = wall.rect.left
                if dx < 0: # Moving left; Hit the right side of the wall
                    self.rect.left = wall.rect.right
                if dy > 0: # Moving down; Hit the top side of the wall
                    self.rect.bottom = wall.rect.top
                if dy < 0: # Moving up; Hit the bottom side of the wall
                    self.rect.top = wall.rect.bottom

# Nice class to hold a wall rect
class Wall(object):
    
    def __init__(self, pos):
        walls.append(self)
        self.rect = pygame.Rect(pos[0], pos[1], 16, 16)

# Initialise pygame
os.environ["SDL_VIDEO_CENTERED"] = "1"
pygame.init()

# Set up the display
pygame.display.set_caption("Get to the red square!")
screen = pygame.display.set_mode((400, 300))

clock = pygame.time.Clock()
walls = [] # List to hold the walls
player = Player() # Create the player


# Holds the level layout in a list of strings.
level = [
    "WWWWWWWWWWWWWWWWWWWW",
    "W                  W",
    "W         WWWWWW   W",
    "W   WWWW       W   W",
    "W   W        WWWW  W",
    "W WWW  WWWW        W",
    "W   W     W W      W",
    "W   W     W   WWW WW",
    "W   WWW WWW   W W  W",
    "W     W   W   W W  W",
    "WWW   W   WWWWW W  W",
    "W W      WW        W",
    "W W   WWWW   WWW   W",
    "W     W    E   W   W",
    "WWWWWWWWWWWWWWWWWWWW",
]

# Parse the level string above. W = wall, E = exit
x = y = 0
for row in level:
    for col in row:
        if col == "W":
            Wall((x, y))
        if col == "E":
            end_rect = pygame.Rect(x, y, 16, 16)
        x += 16
    y += 16
    x = 0

running = True
while running:
    
    clock.tick(60)
    
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            running = False

    # Move the player if an arrow key is pressed
    key = pygame.key.get_pressed()
    if key[pygame.K_LEFT]:
        (x, y) = player.shift_direction(player.move_angle, player.shift_speed)
    if key[pygame.K_RIGHT]:
        (x, y) = player.shift_direction(player.move_angle, -player.shift_speed)
    else:
        (x, y) = player.shift_direction(player.move_angle, 0)

    player.move(x, y)

    # Just added this to make it slightly fun ;)
    if player.rect.colliderect(end_rect):
        pygame.quit()
        sys.exit()

    # Draw the scene
    screen.fill((0, 0, 0))
    for wall in walls:
        pygame.draw.rect(screen, (255, 255, 255), wall.rect)
    pygame.draw.rect(screen, (255, 0, 0), end_rect)
    pygame.draw.rect(screen, (255, 200, 0), player.rect)
    # gfxdraw.filled_circle(screen, 255, 200, 5, (0,128,0))
    pygame.display.flip()
    clock.tick(360)

pygame.quit()