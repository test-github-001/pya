import sys
import pygame as PG
import random
import math

PG.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

SCREEN = PG.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
PG.display.set_caption("Платформер")
CLOCK = PG.time.Clock()

FPS = 60

PLATFORM_HEIGHT = 40
PLATFORM_WIDTH_STEP = 40
PLATFORM_COLOR = (0, 255, 0)
FINISH_COLOR = (255, 255, 0)

# Новые размеры игрока
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 60
PLAYER_SPEED = 5
PLAYER_COLOR = (255, 0, 0)
JUMP_FORCE = -15
GRAVITY = 0.5

# Уровень:
# строки одинаковой длины,
# символы между [ ] = платформа,
# P = игрок, F = финиш, E = враг
level = [
    '                                        ',
    '                                        ',
    '                                        ',
    '[=]                [===F===]            ',
    '        [=]    [E]           [=]     [=]',
    '[=]                [=======]            ',
    '        [E]    [=]           [E]     [=]',
    '[=]                [=======]            ',
    '        [=]    [E]           [=]     [=]',
    '[=]                [=======]            ',
    '        [=]    [=]           [=]     [=]',
    '[==P=======================E===========]',
]

step_x = PLATFORM_WIDTH_STEP
step_y = PLATFORM_HEIGHT + PLAYER_HEIGHT + 20  # вертикальный шаг между строками

LEVEL_WIDTH = len(level[0]) * step_x
LEVEL_HEIGHT = len(level) * step_y

# Классы
class Background:
    def __init__(self, image, parallax_scale=1.5):
        bg = PG.image.load(image).convert()
        min_w = int(LEVEL_WIDTH * 1.5)
        min_h = int(LEVEL_HEIGHT * 1.5)
        w, h = bg.get_size()
        scale = max(min_w / w, min_h / h)
        self.image = PG.transform.scale(bg, (int(w*scale), int(h*scale)))
        self.w, self.h = self.image.get_size()
        self.parallax = 1.0 / parallax_scale

    def draw(self, camera):
        lvl_cx = LEVEL_WIDTH / 2
        lvl_cy = LEVEL_HEIGHT / 2
        bg_cx = self.w / 2
        bg_cy = self.h / 2
        bg_x = (camera.x - lvl_cx) * self.parallax + bg_cx - SCREEN_WIDTH / 2
        bg_y = (camera.y - lvl_cy) * self.parallax + bg_cy - SCREEN_HEIGHT / 2
        bg_x = int( max(0, min(bg_x, self.w - SCREEN_WIDTH)) )
        bg_y = int( max(0, min(bg_y, self.h - SCREEN_HEIGHT)) )
        SCREEN.blit(self.image, (0, 0), (bg_x, bg_y, SCREEN_WIDTH, SCREEN_HEIGHT))

class SpriteSheet:
    def __init__(self, filename):
        self.sheet = PG.image.load(filename).convert_alpha()
        
    def get_frame(self, col, row):
        """Вырезаем кадр 100x150px из спрайт-листа"""
        # Кадр 100x150px с отступами по 1px с каждой стороны
        x = col * 102 + 1  # 102 = 100 + 1 + 1
        y = row * 152 + 1  # 152 = 150 + 1 + 1
        frame = PG.Surface((100, 150), PG.SRCALPHA)
        frame.blit(self.sheet, (0, 0), (x, y, 100, 150))
        return frame

class PlatformSprite:
    def __init__(self, filename):
        self.sheet = PG.image.load(filename).convert_alpha()
        self.left_sprite = self._get_sprite_part(0, 0, 40, 40)
        self.middle_sprite = self._get_sprite_part(40, 0, 40, 40)
        self.right_sprite = self._get_sprite_part(80, 0, 40, 40)
        
    def _get_sprite_part(self, x, y, width, height):
        """Вырезаем часть спрайта платформы"""
        sprite = PG.Surface((width, height), PG.SRCALPHA)
        sprite.blit(self.sheet, (0, 0), (x, y, width, height))
        return sprite
        
    def draw_platform(self, screen, x, y, width_cells, is_finish=False, camera=None):
        """Отрисовываем платформу из частей"""
        screen_x = x if camera is None else x - camera.x
        screen_y = y if camera is None else y - camera.y
        
        # Для всех платформ используем спрайты
        for i in range(width_cells):
            cell_x = screen_x + i * PLATFORM_WIDTH_STEP
            
            if width_cells == 1:
                # Одиночная платформа - используем среднюю часть
                screen.blit(self.middle_sprite, (cell_x, screen_y))
            else:
                if i == 0:
                    # Левый край
                    screen.blit(self.left_sprite, (cell_x, screen_y))
                elif i == width_cells - 1:
                    # Правый край
                    screen.blit(self.right_sprite, (cell_x, screen_y))
                else:
                    # Середина
                    screen.blit(self.middle_sprite, (cell_x, screen_y))

class FinishTarget:
    def __init__(self, x, y):
        self.original_image = PG.image.load('./src/sprites/target.png').convert_alpha()
        # Масштабируем до 50x50px
        self.original_image = PG.transform.scale(self.original_image, (50, 50))
        self.rect = PG.Rect(x + 20, y - 60, 40, 40)  # Коллайдер 40x40, приподнят над платформой
        self.animation_timer = 0
        self.animation_speed = 0.02
        
    def update(self):
        self.animation_timer += self.animation_speed
        
    def draw(self, camera):
        # Анимация масштаба по оси X (иллюзия вращения)
        scale_x = 0.52 + 0.48 * math.sin(self.animation_timer * 2)
        current_image = PG.transform.scale(self.original_image, (int(50 * scale_x), 50))
        
        # Центрируем изображение относительно коллайдера
        image_rect = current_image.get_rect()
        image_rect.center = (self.rect.centerx - camera.x, self.rect.centery - camera.y)
        
        SCREEN.blit(current_image, image_rect)

class Enemy:
    def __init__(self, x, y):
        self.original_image = PG.image.load('./src/sprites/enemy.png').convert_alpha()
        # Масштабируем до размеров игрока
        self.original_image = PG.transform.scale(self.original_image, (50, 75))
        self.rect = PG.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.animation_timer = 0
        self.animation_speed = 0.05
        self.start_y = y
        self.levitation_height = 50
        
    def update(self):
        self.animation_timer += self.animation_speed
        # Анимация левитации (подлетает и опускается)
        self.rect.y = self.start_y - math.sin(self.animation_timer) * self.levitation_height
        
    def draw(self, camera):
        screen_x = self.rect.centerx - camera.x
        screen_y = self.rect.centery - camera.y
        
        image_rect = self.original_image.get_rect()
        image_rect.center = (screen_x, screen_y)
        
        SCREEN.blit(self.original_image, image_rect)

class Player:
    def __init__(self, x, y):
        # Загружаем спрайт-лист
        self.sprite_sheet = SpriteSheet('./src/sprites/hero.png')
        
        # Масштаб для спрайта 50x75px (0.5 от оригинального размера)
        self.scale = 0.5
        
        # Создаем словарь анимаций
        self.animations = self._create_animations()
        
        # Текущее состояние
        self.current_animation = 'idle'
        self.current_frame = 0
        self.animation_speed = 0.15
        self.animation_timer = 0
        
        # Направление (True - вправо, False - влево)
        self.facing_right = True
        
        # Состояния для анимаций
        self.was_on_ground = True
        self.jump_start_played = False
        self.jump_end_played = False
        
        # rect — прямоугольник персонажа (позиция + размер) - коллайдер 40x60
        self.rect = PG.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.speed_x = 0
        self.speed_y = 0
        self.is_on_ground = False

    def _create_animations(self):
        animations = {}
        
        # idle -> 9 кадров (вся 1я строка и левый кадр 2й строки)
        idle_frames = []
        for col in range(8):  # вся 1 строка
            frame = self.sprite_sheet.get_frame(col, 0)
            frame = PG.transform.scale(frame, (50, 75))  # масштаб 0.5
            idle_frames.append(frame)
        # левый кадр 2 строки
        frame = self.sprite_sheet.get_frame(0, 1)
        frame = PG.transform.scale(frame, (50, 75))
        idle_frames.append(frame)
        animations['idle'] = idle_frames
        
        # run -> 12 кадров (вся 2я строка кроме левого кадра и 5 левых кадров 3й строки)
        run_frames = []
        # 2 строка кроме левого кадра (колонки 1-7)
        for col in range(1, 8):
            frame = self.sprite_sheet.get_frame(col, 1)
            frame = PG.transform.scale(frame, (50, 75))
            run_frames.append(frame)
        # 5 левых кадров 3 строки
        for col in range(5):
            frame = self.sprite_sheet.get_frame(col, 2)
            frame = PG.transform.scale(frame, (50, 75))
            run_frames.append(frame)
        animations['run'] = run_frames
        
        # jumpStart -> 1 кадр 6й в 3й строке
        jump_start_frame = self.sprite_sheet.get_frame(5, 2)
        jump_start_frame = PG.transform.scale(jump_start_frame, (50, 75))
        animations['jumpStart'] = [jump_start_frame]
        
        # jump -> 7 кадров (7, 8 кадр 3й строки + 5 левых кадров 4й строки)
        jump_frames = []
        # 7, 8 кадр 3й строки (колонки 6, 7)
        for col in range(6, 8):
            frame = self.sprite_sheet.get_frame(col, 2)
            frame = PG.transform.scale(frame, (50, 75))
            jump_frames.append(frame)
        # 5 левых кадров 4й строки
        for col in range(5):
            frame = self.sprite_sheet.get_frame(col, 3)
            frame = PG.transform.scale(frame, (50, 75))
            jump_frames.append(frame)
        animations['jump'] = jump_frames
        
        # jumpEnd -> 2 кадра - 6й и 7й в 4й строке
        jump_end_frames = []
        for col in range(5, 7):  # 6й и 7й кадры
            frame = self.sprite_sheet.get_frame(col, 3)
            frame = PG.transform.scale(frame, (50, 75))
            jump_end_frames.append(frame)
        animations['jumpEnd'] = jump_end_frames
        
        return animations

    def update_animation(self):
        # Определяем новое состояние анимации
        new_animation = self.current_animation
        
        if not self.is_on_ground:
            if not self.jump_start_played:
                new_animation = 'jumpStart'
                self.jump_start_played = True
                self.jump_end_played = False
            else:
                new_animation = 'jump'
        else:
            if not self.was_on_ground and not self.jump_end_played:
                new_animation = 'jumpEnd'
                self.jump_end_played = True
            elif self.speed_x != 0:
                new_animation = 'run'
            else:
                new_animation = 'idle'
            
            if self.is_on_ground:
                self.jump_start_played = False

        # Если анимация изменилась, сбрасываем кадр
        if new_animation != self.current_animation:
            self.current_animation = new_animation
            self.current_frame = 0
            self.animation_timer = 0

        # Обновляем таймер анимации
        self.animation_timer += self.animation_speed
        
        # Переходим к следующему кадру, если таймер достиг 1
        if self.animation_timer >= 1:
            animation_frames = self.animations[self.current_animation]
            
            # Для нециклических анимаций проверяем конец
            if self.current_animation in ['jumpStart', 'jumpEnd']:
                if self.current_frame < len(animation_frames) - 1:
                    self.current_frame += 1
                else:
                    # Анимация закончилась, переключаемся на следующую
                    if self.current_animation == 'jumpStart':
                        self.current_animation = 'jump'
                    elif self.current_animation == 'jumpEnd':
                        self.current_animation = 'idle'
                    self.current_frame = 0
            else:
                # Циклические анимации (idle, run, jump)
                self.current_frame = (self.current_frame + 1) % len(animation_frames)
            
            self.animation_timer = 0

        self.was_on_ground = self.is_on_ground

    def apply_input(self, keys):
        self.speed_x = 0
        if keys[PG.K_LEFT] or keys[PG.K_a]:
            self.speed_x = -PLAYER_SPEED
            self.facing_right = False
        if keys[PG.K_RIGHT] or keys[PG.K_d]:
            self.speed_x = PLAYER_SPEED
            self.facing_right = True

    def jump(self):
        # прыгаем только если на земле
        if self.is_on_ground:
            self.speed_y = JUMP_FORCE
            sfx_jump.play()

    def update(self, platforms, finish_targets, enemies):
        self.speed_y += GRAVITY
        self.rect.x += self.speed_x
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.speed_x > 0:
                    self.rect.right = p.rect.left
                elif self.speed_x < 0:
                    self.rect.left = p.rect.right

        self.rect.y += self.speed_y
        self.is_on_ground = False
        level_complete = False
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.speed_y > 0:
                    self.rect.bottom = p.rect.top
                    self.is_on_ground = True
                    self.speed_y = 0
                elif self.speed_y < 0:
                    self.rect.top = p.rect.bottom
                    self.speed_y = 0

        # Проверка столкновения с финишем
        for target in finish_targets:
            if self.rect.colliderect(target.rect):
                level_complete = True

        # Проверка столкновения с врагами
        for enemy in enemies:
            if self.rect.colliderect(enemy.rect):
                return 'game_over'

        # ограничения по границам уровня
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(LEVEL_WIDTH, self.rect.right)
        self.rect.bottom = min(LEVEL_HEIGHT, self.rect.bottom)
        
        # Обновляем анимацию
        self.update_animation()
        
        return 'win' if level_complete else 'continue'

    def draw(self, camera):
        # Безопасное получение текущего кадра
        try:
            current_image = self.animations[self.current_animation][self.current_frame]
        except IndexError:
            # Если возникла ошибка, сбрасываем на первый кадр
            print(f"Animation error: {self.current_animation}[{self.current_frame}]")
            self.current_frame = 0
            current_image = self.animations[self.current_animation][self.current_frame]
        
        # Отражаем если смотрим влево
        if not self.facing_right:
            current_image = PG.transform.flip(current_image, True, False)
            
        # Позиционируем спрайт (центрируем относительно rect)
        sprite_rect = current_image.get_rect()
        sprite_rect.midbottom = (self.rect.centerx - camera.x, self.rect.bottom - camera.y)
        
        SCREEN.blit(current_image, sprite_rect)

class Platform:
    def __init__(self, x, y, width_cells, is_finish=False):
        self.rect = PG.Rect(x, y, width_cells * PLATFORM_WIDTH_STEP, PLATFORM_HEIGHT)
        self.is_finish = is_finish
        self.width_cells = width_cells

    def draw(self, camera, platform_sprite):
        platform_sprite.draw_platform(SCREEN, self.rect.x, self.rect.y, 
                                    self.width_cells, self.is_finish, camera)

class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0
    def update(self, target):
        self.x = target.rect.centerx - SCREEN_WIDTH // 2
        self.y = target.rect.centery - SCREEN_HEIGHT // 2
        self.x = max(0, min(self.x, LEVEL_WIDTH - SCREEN_WIDTH))
        self.y = max(0, min(self.y, LEVEL_HEIGHT - SCREEN_HEIGHT))

def generate_level(lines):
    platforms = []
    finish_targets = []
    enemies = []
    player = None
    y = 0
    for line in lines:
        x = 0
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '[':
                # начинаем читать блок до закрывающей ']' и считаем ширину
                j = i + 1
                block = ''
                is_finish = False
                finish_position = -1
                enemy_positions = []  # храним позиции врагов внутри платформы
                
                while j < len(line) and line[j] != ']':
                    if line[j] == 'F':
                        is_finish = True
                        finish_position = j - i - 1  # позиция F внутри блока
                    elif line[j] == 'E':
                        # Запоминаем позицию врага внутри платформы
                        enemy_positions.append(j - i - 1)
                    block += line[j]
                    j += 1
                
                # Ширина платформы = количество символов между [ и ] + 2 (сами скобки)
                width_cells = len(block) + 2
                # создаём платформу
                p = Platform(x, y, width_cells, is_finish=is_finish)
                platforms.append(p)
                
                # Если это финишная платформа, создаем target
                if is_finish and finish_position != -1:
                    # Вычисляем позицию target по центру платформы
                    target_x = x + (finish_position + 1) * PLATFORM_WIDTH_STEP
                    target = FinishTarget(target_x, y)
                    finish_targets.append(target)
                
                # Создаем врагов внутри платформы
                for enemy_pos in enemy_positions:
                    enemy_x = x + (enemy_pos + 1) * PLATFORM_WIDTH_STEP
                    enemy = Enemy(enemy_x, y - PLAYER_HEIGHT)
                    enemies.append(enemy)
                
                # сдвигаем курсор и x на ширину блока + скобки
                x += PLATFORM_WIDTH_STEP * width_cells
                i = j + 1
                continue
            elif ch == 'P':
                # игрок размещается сверху от "пола" ячейки
                player = Player(x, y - PLAYER_HEIGHT)
            elif ch == 'E':
                # враг размещается сверху от "пола" ячейки (отдельный, не в платформе)
                enemy = Enemy(x, y - PLAYER_HEIGHT)
                enemies.append(enemy)
            # обычный шаг вправо на одну ячейку
            x += PLATFORM_WIDTH_STEP
            i += 1
        y += step_y

    return platforms, player, finish_targets, enemies

# Загружаем спрайты
BG = Background(f'./src/sprites/bg{random.randint(1, 4)}.png') 
platform_sprite = PlatformSprite('./src/sprites/platform.png')

PG.mixer.music.load('./src/sounds/bgm_1.mp3')
PG.mixer.music.set_volume(0.7)
PG.mixer.music.play(-1)

sfx_jump = PG.mixer.Sound('./src/sounds/sfx_bonus.mp3')

def reset_game():
    global platforms, player, finish_targets, enemies, camera, is_game_won, game_over, game_over_timer
    platforms, player, finish_targets, enemies = generate_level(level)
    camera = Camera()
    if player is None:
        player = Player(LEVEL_WIDTH // 2, LEVEL_HEIGHT // 2)
    is_game_won = False
    game_over = False
    game_over_timer = 0

# Инициализация игры
platforms, player, finish_targets, enemies = generate_level(level)
camera = Camera()
if player is None:
    player = Player(LEVEL_WIDTH // 2, LEVEL_HEIGHT // 2)

is_running = True
is_game_won = False
game_over = False
game_over_timer = 0

# --- Вспомогательные функции для чистоты цикла ---
def handle_events():
    jump_pressed = False
    global is_running
    for event in PG.event.get():
        if event.type == PG.QUIT:
            is_running = False
        elif event.type == PG.KEYDOWN:
            if event.key == PG.K_ESCAPE:
                is_running = False
            elif event.key == PG.K_SPACE:
                jump_pressed = True
    return jump_pressed

def draw_win():
    font = PG.font.Font(None, 74)
    text = font.render("ПОБЕДА!", True, (255, 255, 0))
    SCREEN.blit(text, text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))

def draw_game_over():
    font = PG.font.Font(None, 74)
    text = font.render("ПОТРАЧЕНО", True, (255, 0, 0))
    SCREEN.blit(text, text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))

# --- Главный цикл ---
while is_running:
    CLOCK.tick(FPS)
    jump = handle_events()

    if not is_game_won and not game_over:
        keys = PG.key.get_pressed()
        player.apply_input(keys)
        if jump:
            player.jump()
        
        # Обновляем анимации финиша и врагов
        for target in finish_targets:
            target.update()
        for enemy in enemies:
            enemy.update()
        
        # Отладочный вывод для проверки врагов
        if PG.time.get_ticks() % 1000 < 50:  # Выводим раз в секунду
            print(f"Enemies count: {len(enemies)}, Player pos: ({player.rect.x}, {player.rect.y})")
        
        # Обновляем игрока и проверяем состояние
        result = player.update(platforms, finish_targets, enemies)
        if result == 'win':
            is_game_won = True
        elif result == 'game_over':
            game_over = True
            game_over_timer = PG.time.get_ticks()
        
        camera.update(player)
    elif game_over:
        # Ждем 2 секунды после проигрыша и перезапускаем игру
        if PG.time.get_ticks() - game_over_timer > 2000:
            reset_game()

    # отрисовка
    SCREEN.fill((0, 0, 0))
    BG.draw(camera)
    for p in platforms:
        p.draw(camera, platform_sprite)
    for target in finish_targets:
        target.draw(camera)
    for enemy in enemies:
        enemy.draw(camera)
    player.draw(camera)
    
    if is_game_won:
        draw_win()
    elif game_over:
        draw_game_over()
        
    PG.display.flip()

PG.quit()
sys.exit()