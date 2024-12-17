import os
import json
import math
import pygame
import pymunk
import random
import tempfile
import pymunk.pygame_util
import numpy as np
from PIL import Image
from datetime import datetime
from scipy.spatial import ConvexHull

# Claw and GachaBall classes
from claw import Claw
from gacha_ball import GachaBall

# Creates the container where the gacha balls will be contained
def create_container(space):
    container_width = 770  
    container_height = 450 
    center_x = 350  
    center_y = 340  

    half_width = container_width // 2
    half_height = container_height // 2

    # Define the corner points of the box
    top_left = (center_x - half_width, center_y - half_height)
    top_right = (center_x + half_width, center_y - half_height)
    bottom_left = (center_x - half_width, center_y + half_height)
    bottom_right = (center_x + half_width, center_y + half_height)

    # Define static lines forming the box
    static_lines = [
        pymunk.Segment(space.static_body, top_left, top_right, 50),  # Top
        pymunk.Segment(space.static_body, top_right, bottom_right, 50),  # Right
        pymunk.Segment(space.static_body, bottom_right, bottom_left, 50),  # Bottom
        pymunk.Segment(space.static_body, bottom_left, top_left, 50),  # Left
    ]

    # Set elasticity and add lines to the space
    for line in static_lines:
        line.elasticity = 0.6 # Allows the gacha balls to partially bounce off the container
        space.add(line)

# Draws a button on the screen
def draw_button(screen, text, x, y, width, height, color, text_color):
    pygame.draw.rect(screen, (0, 0, 0), (x - 2, y - 2, width + 4, height + 4)) # border
    pygame.draw.rect(screen, color, (x, y, width, height))
    font = pygame.font.Font(None, 20)
    label = font.render(text, True, text_color)
    text_rect = label.get_rect(center=(x + width // 2, y + height // 2))
    screen.blit(label, text_rect)
    return pygame.Rect(x, y, width, height)

# Gets the points around the shape of the claw animation (ensures the game recognizes the different claw shapes)
def get_claw_points_from_surface(surface, scale=1.0):

    # Save the surface to a file
    temp_file = os.path.join(tempfile.gettempdir(), "claw_temp.png")
    pygame.image.save(surface, temp_file)
    
    # Load it with PIL
    img = Image.open(temp_file).convert("RGBA")
    
    # Extract alpha channel and compute convex hull
    alpha = np.array(img)[:, :, 3]
    non_transparent_coords = np.column_stack(np.where(alpha > 0))
    hull = ConvexHull(non_transparent_coords)
    hull_points = non_transparent_coords[hull.vertices]
    
    # Center and scale points
    center_x = (hull_points[:, 1].max() + hull_points[:, 1].min()) // 2
    center_y = (hull_points[:, 0].max() + hull_points[:, 0].min()) // 2
    scaled_points = [
        ((x - center_x) * scale, (y - center_y) * scale)
        for y, x in hull_points
    ]
    
    # Remove temporary file
    os.remove(temp_file)
    
    return scaled_points

# Function to facilitate rotations around its center
def blit_rotate_center(surf, image, topleft, angle):
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center=image.get_rect(topleft=topleft).center)
    surf.blit(rotated_image, new_rect.topleft)

# Display a pop-up overlay showing the prize after grabbing a gacha ball
def show_prize_popup(screen, prize_image):

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))  # Semi-transparent black background
    
    # Draw overlay
    screen.blit(overlay, (0, 0))
    
    # Draw prize text
    font = pygame.font.Font(None, 50)
    text = font.render("Congratulations! You won:", True, (255, 255, 255))
    text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 130))
    screen.blit(text, text_rect)

    # Resize prize image
    original_width, original_height = prize_image.get_size()
    scale_factor = min(150 / original_width, 150 / original_height)
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)
    prize_image = pygame.transform.scale(prize_image, (new_width, new_height))

    # Draw prize image
    prize_rect = prize_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(prize_image, prize_rect)
    
    # Draw instructions
    font_instruction = pygame.font.Font(None, 30)
    instruction_text = font_instruction.render("Press ENTER to continue...", True, (255, 255, 255))
    instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 150))
    screen.blit(instruction_text, instruction_rect)
    
    pygame.display.flip() # Updates the display
    
    # Wait for ENTER key press to continue
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:  # Check if Enter key is pressed
                    waiting = False

# Displays a shelf window showing the prize collection divided into sections and subsections
def display_shelves_with_nested_sections(prize_sections, columns_per_section):
    shelf_width, shelf_height = 700, 700
    shelf_window = pygame.Surface((shelf_width, shelf_height))
    shelf_window.fill((230, 230, 230))  # Light gray background
    section_font = pygame.font.Font(None, 30)
    subsection_font = pygame.font.Font(None, 28)
    padding = 20  # Space between prizes

    # Main section list and navigation variables
    main_sections = list(prize_sections.items())
    total_sections = len(main_sections)
    current_section_index = 0

    # Draws the content of the specified main section.
    def draw_section(section_index):

        shelf_window.fill((230, 230, 230)) # Clears the window
        y_position = 40
        section_name, subsections = main_sections[section_index]

        # Draw main section header
        header_text = section_font.render(section_name, True, (0, 0, 0))
        header_rect = header_text.get_rect(center=(shelf_width // 2, y_position))
        shelf_window.blit(header_text, header_rect)
        y_position += 75  # Space below the header

        for subsection_index, (subsection_name, prizes) in enumerate(subsections.items()):
            # Get the number of columns for this subsection
            columns = columns_per_section[section_index][subsection_index]

            # Draw subsection header
            subheader_text = subsection_font.render(subsection_name, True, (100, 100, 100))
            subheader_rect = subheader_text.get_rect(center=(shelf_width // 2, y_position))
            shelf_window.blit(subheader_text, subheader_rect)
            y_position += 30  # Space below the subsection header

            for i, (name, data) in enumerate(prizes.items()):

                # Load and scale prize image
                image = pygame.image.load(data["image"]).convert_alpha()
                original_width, original_height = image.get_size()
                scale_factor = min(100 / original_width, 100 / original_height)
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)

                # Calculate starting positions for the grid
                grid_width = columns * (new_width + padding) - padding
                start_x = (shelf_width - grid_width) // 2
                row = i // columns
                col = i % columns

                x = start_x + col * (new_width + padding)
                y = y_position + row * (new_height + padding)

                # Draw prize slot background
                slot_rect = pygame.Rect(x - 5, y - 5, new_width + 10, new_height + 10)
                pygame.draw.rect(shelf_window, (200, 200, 200), slot_rect, border_radius=10)

                # Display prize image
                if data["won"]:
                    image = pygame.transform.scale(image, (new_width, new_height))
                else:
                    image = pygame.Surface((new_width, new_height), pygame.SRCALPHA)
                    image.fill((0, 0, 0, 180))  # Dimmed effect for locked prizes

                shelf_window.blit(image, (x, y))

            # Move Y position for the next subsection
            rows = (len(prizes) + columns - 1) // columns  # Calculate the number of rows
            y_position += rows * (new_height + padding) + 10  # Space between subsections

    # Draw navigation buttons for moving between category pages
    def draw_navigation_buttons():
        if current_section_index > 0:  # Left arrow
            pygame.draw.polygon(shelf_window, (0, 0, 0), [(20, shelf_height // 2), (50, shelf_height // 2 - 20), (50, shelf_height // 2 + 20)])
        if current_section_index < total_sections - 1:  # Right arrow
            pygame.draw.polygon(shelf_window, (0, 0, 0), [(shelf_width - 20, shelf_height // 2), (shelf_width - 50, shelf_height // 2 - 20), (shelf_width - 50, shelf_height // 2 + 20)])

    # Main loop for the shelf window
    running = True
    while running:
        draw_section(current_section_index)
        draw_navigation_buttons()
        screen.blit(shelf_window, ((SCREEN_WIDTH - shelf_width) // 2, (SCREEN_HEIGHT - shelf_height) // 2))
        pygame.display.flip()

        # Manages user input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and current_section_index > 0:  # Navigate left
                    current_section_index -= 1
                elif event.key == pygame.K_RIGHT and current_section_index < total_sections - 1:  # Navigate right
                    current_section_index += 1
                elif (event.key == pygame.K_ESCAPE or event.key == pygame.K_SPACE):  # Exit the shelf view
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                if 20 <= mouse_x <= 50 and (shelf_height // 2 - 20) <= mouse_y <= (shelf_height // 2 + 20):  # Left arrow
                    if current_section_index > 0:
                        current_section_index -= 1
                elif (shelf_width - 50) <= mouse_x <= (shelf_width - 20) and (shelf_height // 2 - 20) <= mouse_y <= (shelf_height // 2 + 20):  # Right arrow
                    if current_section_index < total_sections - 1:
                        current_section_index += 1              

# Saves the game progress into JSON file
def save_game_data(game_data, filename='save-file.json'):
    with open(filename, 'w') as file:
        json.dump(game_data, file, indent=4)

# Marks off a prize as unlocked
def markPrize():
    # List of prizes that can be won
    available_prizes = [
        (main_section, subsection, key)
        for main_section, subsections in prize_sections.items()
        for subsection, prizes in subsections.items()
        for key, prize in prizes.items()
        if not prize["won"]
    ]

    if available_prizes: # If a prize is available

        # Randomly select a prize from the available ones
        selected_main_section, selected_subsection, prize_key = random.choice(available_prizes)

        # Mark the prize as won in prize_sections
        prize_sections[selected_main_section][selected_subsection][prize_key]["won"] = True

        # Show the prize popup with the prize image
        prize_image = pygame.image.load(
            prize_sections[selected_main_section][selected_subsection][prize_key]["image"]
        ).convert_alpha()
        show_prize_popup(screen, prize_image)

# Main game loop
def game_loop():
    claw = Claw(SCREEN_WIDTH, space) # Claw declaration
    running = True
    
    last_time = pygame.time.get_ticks()  # Store the time at the start   

    if datetime.now().date() != datetime.fromisoformat(data.get("Last Saved DateTime")).date():
        i = 0 # Gacha balls returns to 20 after the next day
    else:
        i = 20 - data.get("Gacha Balls")

    # Stores the number of coins 
    coinNum = data.get("Coins")

    # Increments coin accumulated during idle time 
    coinNum += int(abs((datetime.now() - datetime.fromisoformat(data.get("Last Saved DateTime"))).total_seconds())/300)

    # Ensures max number of coins is 20
    if coinNum > 20:
        coinNum = 20

    # Loading of left and right buttons
    leftbutton1 = pygame.image.load("images/left-button1.png").convert_alpha()
    leftbutton2 = pygame.image.load("images/left-button2.png").convert_alpha()
    rightbutton1 = pygame.image.load("images//right-button1.png").convert_alpha()
    rightbutton2 = pygame.image.load("images//right-button2.png").convert_alpha()

    # Button positions
    left_button_rect = leftbutton1.get_rect(topleft=(50, 575))
    right_button_rect = rightbutton1.get_rect(topleft=(150, 575))
    transparent_surface = pygame.Surface((100, 100))  # Same size as the screen
    transparent_surface.set_alpha(0)

    # Button flags
    left_pressed = False
    right_pressed = False

    while running:
        screen.fill((0, 0, 0))  # Clear screen
        screen.blit(background_image, (0, 0))  # Draw background
        screen.blit(logo, (295, 10))
        # Number of coins text
        font = pygame.font.Font(None, 64)
        text_surface = font.render(str(coinNum) + "x", True, (81, 87, 120))
        text_rect = text_surface.get_rect(center=(475, 618))
        screen.blit(text_surface, text_rect)

        # Draws Show Prizes button
        button_rect = draw_button(screen, "Show Prizes", 570, 540, 100, 50, (255, 173, 192), (0, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT: # On termination of game
                # Stores data to be saved in a dictionary
                game_data = {
                    "Last Saved DateTime": datetime.now().isoformat(),
                    "Coins": coinNum,
                    "Gacha Balls": len(gacha_prizes),
                    "Prizes": prize_sections
                }
                save_game_data(game_data)
                running = False
            if event.type == spawn_event:
                if i < 20:
                    gacha_prizes.append(GachaBall(space)) # Adds gacha balls to the list
                    i += 1
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s: # Shuffles gacha balls on 's' key press
                    for gacha_ball in gacha_prizes:
                        gacha_ball.shuffle()
                if event.key == pygame.K_LEFT and claw.state == "idle":  # Only move if in idle state
                    claw.x = max(100, claw.x - claw.SPEED)  # Stay within bounds
                    left_pressed = True
                if event.key == pygame.K_RIGHT and claw.state == "idle":  
                    claw.x = min(SCREEN_WIDTH - 100, claw.x + claw.SPEED)
                    right_pressed = True
                if event.key == pygame.K_SPACE and claw.state == "idle":  # Space to descend claw if idle
                    if coinNum > 0:
                        claw.state = "descending"
                        coinNum -= 1
            if event.type == pygame.KEYUP: # Ensures buttons follow key press
                if event.key == pygame.K_LEFT:
                    left_pressed = False
                if event.key == pygame.K_RIGHT:
                    right_pressed = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos): # Show Prizes
                    display_shelves_with_nested_sections(prize_sections, [[3, 5, 3], [3, 5, 3], [3, 5, 3], [3, 5, 3]])
                if left_button_rect.collidepoint(event.pos):
                    left_pressed = True
                if right_button_rect.collidepoint(event.pos):
                    right_pressed = True
            if event.type == pygame.MOUSEBUTTONUP:
                if left_button_rect.collidepoint(event.pos):
                    left_pressed = False
                if right_button_rect.collidepoint(event.pos):
                    right_pressed = False
        if claw.state == "idle":
            if left_pressed:
                screen.blit(leftbutton2, left_button_rect)  # Show pressed image for left button
                claw.x = max(100, claw.x - claw.SPEED)
            else:
                screen.blit(leftbutton1, left_button_rect)  # Show normal image for left button

            if right_pressed:
                screen.blit(rightbutton2, right_button_rect)  # Show pressed image for right button
                claw.x = min(SCREEN_WIDTH - 100, claw.x + claw.SPEED)
            else:
                screen.blit(rightbutton1, right_button_rect)  # Show normal image for right button
        else:
            screen.blit(leftbutton1, left_button_rect)
            screen.blit(rightbutton1, right_button_rect)

        # Update claw body position for physics
        claw.body.position = (claw.x, claw.body.position.y)

        # Handle claw descending
        if claw.state == "descending":
            claw.descend(gacha_prizes, claw_points_close_list)
        # Handle claw ascending
        elif claw.state == "ascending":
            if (claw.ascend(gacha_prizes, claw_points_open_list)):
                markPrize()
                
        # Draw claw
        angle = math.degrees(claw.body.angle)
        claw_image = (
            claw_animation_open[claw.current_frame]
            if claw.state == "ascending"
            else claw_animation_close[claw.current_frame]
        )

        # Updates claw
        blit_rotate_center(
            screen,
            claw_image,
            (
                claw.body.position.x - claw_image.get_width() // 2,
                claw.body.position.y - claw_image.get_height() // 2,
            ),
            -angle,
        )

        # Draw gacha balls in gacha_prizes list
        for gacha_ball in gacha_prizes:
            body = gacha_ball.body
            angle = math.degrees(body.angle)
            x, y = body.position
            blit_rotate_center(screen, ball_image, (x - 40, y - 40), -angle)

        current_time = pygame.time.get_ticks()
        interval = 60000  # 1 minute

        # Check if a minute has passed
        if current_time - last_time >= interval:
            coinNum += 1
            # Reset the minute timer
            last_time = current_time

        # Step the physics simulation
        space.step(1 / FPS)
        pygame.display.flip() # Update display
        clock.tick(FPS) # Maintain FPS
    pygame.quit()

# Initialize Pygame
pygame.init()

# Screen dimensions constants
SCREEN_WIDTH = 700
SCREEN_HEIGHT = 700

# Set up display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Claw Machine Game")
space = pymunk.Space()
space.gravity = (0, 900)
FPS = 60
draw_options = pymunk.pygame_util.DrawOptions(screen)

# Load images
claw_image1 = pygame.image.load("images/claw1.png").convert_alpha()
claw_image2 = pygame.image.load("images/claw2.png").convert_alpha()
claw_image3 = pygame.image.load("images/claw3.png").convert_alpha()
ball_image = pygame.image.load("images/gacha.png").convert_alpha()
background_image = pygame.image.load("images/machine.png").convert_alpha()
logo = pygame.image.load("images/logo.png").convert_alpha()

# Resize images
ball_image = pygame.transform.scale(ball_image, (70, 70))
logo = pygame.transform.scale(logo, (120, 120))

# Lists of frames (for claw animation)
claw_animation_close = [claw_image1, claw_image2, claw_image3]  
claw_animation_open = [claw_image3, claw_image2, claw_image1]

create_container(space)

gacha_prizes = [] # List to store gacha balls

# Lists of the claw points (following the claw animation shape)
claw_points_close_list = [get_claw_points_from_surface(image) for image in claw_animation_close]
claw_points_open_list = [get_claw_points_from_surface(image) for image in claw_animation_open]

# Timer event for spawning gacha balls
spawn_event = pygame.USEREVENT + 1
pygame.time.set_timer(spawn_event, 500)  # Spawns a ball every 0.5 seconds

# Loads data from JSON file into a dictionary
filename = 'save-file.json'
with open(filename, 'r') as file:
    data = json.load(file)

# Stores the 'Prizes' sections and its sub-section in a JSON format
prize_sections = data.get("Prizes", {})

# Initializes the clock for timers
clock = pygame.time.Clock()

# Run the game loop
game_loop()
