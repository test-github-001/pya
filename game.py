import sys
import pygame as PG
PG.init()

SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)

SCREEN = PG.display.set_mode(SCREEN_SIZE)

FPS = 60
CLOCK = PG.time.Clock()

hero_images = []
for i in range(1, 33):
    hero_images.append( PG.image.load(f'./hero/{i}.png') )

class Hero():
    def __init__(self, x, y, images, lastFrame):
        self.rect = PG.Rect(x, y, 43, 48)
        self.images = images
        self.start_image_index = 0
        self.last_image_index = lastFrame
        self.current_image_index = 0
        self.frame_timeout = 45
        self.frame_delay = self.frame_timeout

    def update(self, delta_time):
        self.frame_delay -= delta_time
        if self.frame_delay <= 0:
            self.frame_delay += self.frame_timeout
            self.current_image_index += 1
            if self.current_image_index > self.last_image_index:
                self.current_image_index = self.start_image_index

        self.draw()
    
    def draw(self):
        SCREEN.blit(self.images[self.current_image_index], self.rect)

hero = Hero(200, 200, hero_images, 9)

is_game_running = True
while is_game_running:
    delta_time = CLOCK.tick(FPS) # int(16.6666666666) ~ 16...17

    events = PG.event.get()
    for event in events:
        if event.type == PG.QUIT:
            is_game_running = False
        elif event.type == PG.KEYDOWN and event.key == PG.K_ESCAPE:
            is_game_running = False

    SCREEN.fill( (0, 255, 0) )

    hero.update(delta_time)

    PG.display.flip()

PG.quit()
sys.exit()
