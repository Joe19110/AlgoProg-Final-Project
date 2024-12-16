import pygame
import numpy as np
import pymunk
import pymunk.pygame_util
import random
import math
from PIL import Image
import os
import tempfile
import json
from scipy.spatial import ConvexHull
from datetime import datetime
import time

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 700
SCREEN_HEIGHT = 700

# Set up display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Claw Machine Game")
clock = pygame.time.Clock()
space = pymunk.Space()
space.gravity = (0, 900)
FPS = 60
draw_options = pymunk.pygame_util.DrawOptions(screen)

# Load images
claw_image1 = pygame.image.load("images/claw1.png").convert_alpha()  # Transparent background
claw_image2 = pygame.image.load("images/claw2.png").convert_alpha()
claw_image3 = pygame.image.load("images/claw3.png").convert_alpha()
ball_image = pygame.image.load("images/gacha.png").convert_alpha()  # Add more as needed
background_image = pygame.image.load("images/machine.png").convert_alpha()
# Resize images

ball_image = pygame.transform.scale(ball_image, (70, 70))

claw_animation_close = [claw_image1, claw_image2, claw_image3]  # List of frames
claw_animation_open = [claw_image3, claw_image2, claw_image1]
current_frame = 0  # Track current frame in animation
frame_delay = 5  # Delay before switching to the next frame
frame_counter = 0  # Counter to track frame delays
def get_claw_points_from_surface(surface, scale=1.0):
    """Extract claw points from a Pygame surface."""
    temp_file = os.path.join(tempfile.gettempdir(), "claw_temp.png")
    
    # Save the surface to a file
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
    
    # Clean up temporary file
    os.remove(temp_file)
    
    return scaled_points

def create_container(space):
    container_width = 770  # Width of the container
    container_height = 450  # Height of the container
    center_x = 350  # Screen center x-coordinate
    center_y = 340  # Desired y-coordinate for the center of the container

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
        line.elasticity = 0.6
        space.add(line)


create_container(space)
gacha_prizes = []  # Start with an empty list of gacha balls

# Create gacha balls
def create_gacha_ball(space):

    # Randomize spawn position within the container, but within container bounds
    spawn_x = random.randint(29, 30)
    spawn_y = 150

    body = pymunk.Body(1, pymunk.moment_for_circle(1, 0, 15))
    body.position = spawn_x, spawn_y  # Spawn inside the container area
    shape = pymunk.Circle(body, 35)
    shape.elasticity = 0.8
    shape.friction = 0.5
    shape.collision_type = 1
    space.add(body, shape)
    return body, shape


claw_points_close_list = [get_claw_points_from_surface(image) for image in claw_animation_close]
claw_points_open_list = [get_claw_points_from_surface(image) for image in claw_animation_open]
# Example: Update the claw shape dynamically
current_frame = 0  # Keep track of the current animation frame
claw_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)  # Replace points[] with claw polygon points



def update_claw_shape(space, claw_body, claw_points_list, current_frame):
    """Update the claw shape based on the current animation frame."""
    # Remove the old shapes from the body and the space
    for shape in claw_body.shapes:
        space.remove(shape)
    
    # Add the body to the space (if not already added)
    if claw_body not in space.bodies:
        space.add(claw_body)

    # Create a new claw shape
    new_claw_points = claw_points_list[current_frame]
    claw_shape = pymunk.Poly(claw_body, new_claw_points)
    claw_shape.elasticity = 0.4
    claw_shape.friction = 0.5

    # Add the new shape to the space
    space.add(claw_shape)

    return claw_shape




def blit_rotate_center(surf, image, topleft, angle):
    """Helper function to rotate an image around its center."""
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center=image.get_rect(topleft=topleft).center)
    surf.blit(rotated_image, new_rect.topleft)

# Timer event for spawning gacha balls
spawn_event = pygame.USEREVENT + 1
pygame.time.set_timer(spawn_event, 500)  # Spawn a ball every 2 seconds
def check_claw_grab(claw_shape, gacha_prizes, grab_radius=40, grab_chance=1):
    """Checks for collision between claw and balls."""
    for body, shape in gacha_prizes:
        # Check distance between the claw's center and the prize's center
        claw_pos = claw_shape.body.position
        prize_pos = body.position
        distance = (claw_pos - prize_pos).length  # Vector distance

        if distance <= grab_radius:  # Check if within grab radius
            if random.random() <= grab_chance:  # Check grab chance
                print("Ball grabbed!")
                return body, shape  # Return grabbed ball
    return None
def shuffle_balls(gacha_prizes, intensity=500):
    """
    Apply random forces to all gacha balls to shuffle them.
    
    Args:
        gacha_prizes (list): List of tuples (body, shape) representing the balls.
        intensity (float): The magnitude of the random forces.
    """
    for body, shape in gacha_prizes:
        # Generate random force components
        force_x = random.uniform(-intensity, intensity)
        force_y = random.uniform(-intensity, intensity)
        
        # Apply the force to the ball's body
        body.apply_impulse_at_local_point((force_x, force_y))
def show_prize_popup(screen, prize_image):
    """
    Display a pop-up overlay showing the prize.
    
    Args:
        screen (pygame.Surface): The game screen.
        prize_image (pygame.Surface): The image of the prize won.
    """
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))  # Semi-transparent black background
    
    # Draw overlay
    screen.blit(overlay, (0, 0))
    
    # Draw prize text
    font = pygame.font.Font(None, 50)
    text = font.render("Congratulations! You won:", True, (255, 255, 255))
    text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 130))
    screen.blit(text, text_rect)
    original_width, original_height = prize_image.get_size()
    scale_factor = min(150 / original_width, 150 / original_height)
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)
    # Draw prize image
    prize_image = pygame.transform.scale(prize_image, (new_width, new_height))
    prize_rect = prize_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(prize_image, prize_rect)
    
    # Draw instructions
    font_instruction = pygame.font.Font(None, 30)
    instruction_text = font_instruction.render("Press any key to continue...", True, (255, 255, 255))
    instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 150))
    screen.blit(instruction_text, instruction_rect)
    
    pygame.display.flip()
    
    # Wait for key press to continue
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                waiting = False

def draw_button(screen, text, x, y, width, height, color, text_color):
    """
    Draw a button on the screen.
    """
    pygame.draw.rect(screen, (0, 0,0), (x - 2, y - 2, width + 4, height + 4))
    pygame.draw.rect(screen, color, (x, y, width, height))
    font = pygame.font.Font(None, 20)
    label = font.render(text, True, text_color)
    text_rect = label.get_rect(center=(x + width // 2, y + height // 2))
    screen.blit(label, text_rect)
    return pygame.Rect(x, y, width, height)
def display_shelves_with_nested_sections(prize_sections, columns_per_section):
    """
    Display a shelf window showing the prize collection divided into sections
    and subsections, with configurable columns per section or subsection.
    Navigation between sections is handled with arrow buttons.
    """
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

    def draw_section(section_index):
        """
        Draw the content of the specified main section.
        """
        shelf_window.fill((230, 230, 230))  # Clear the window
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

    def draw_navigation_buttons():
        """
        Draw navigation buttons for moving between sections.
        """
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

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and current_section_index > 0:  # Navigate left
                    current_section_index -= 1
                elif event.key == pygame.K_RIGHT and current_section_index < total_sections - 1:  # Navigate right
                    current_section_index += 1
                elif event.key == pygame.K_ESCAPE:  # Exit the shelf view
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos
                if 20 <= mouse_x <= 50 and (shelf_height // 2 - 20) <= mouse_y <= (shelf_height // 2 + 20):  # Left arrow
                    if current_section_index > 0:
                        current_section_index -= 1
                elif (shelf_width - 50) <= mouse_x <= (shelf_width - 20) and (shelf_height // 2 - 20) <= mouse_y <= (shelf_height // 2 + 20):  # Right arrow
                    if current_section_index < total_sections - 1:
                        current_section_index += 1

claw_state = "idle"  # States: "idle", "descending", "ascending"
grabbed_ball = None
original_claw_y = 210
target_claw_y = 450  # How far the claw should descend
# Define the filename of the JSON file
filename = 'save-file.json'

# Open the file in read mode and load the JSON data into a Python dictionary
with open(filename, 'r') as file:
    data = json.load(file)

# Access the 'Prizes' section only
prize_sections = data.get("Prizes", {})



def save_game_data(game_data, filename='save-file.json'):
    with open(filename, 'w') as file:
        json.dump(game_data, file, indent=4)
def game_loop():
    global claw_state, grabbed_ball, claw_body, current_frame, frame_counter, ballNum
    claw_x = SCREEN_WIDTH // 2  # Initial claw X position
    claw_body.position = (claw_x, original_claw_y)  # Initial claw position
    claw_speed = 5
    claw_state = "idle"
    running = True
    coinNum = data.get("Coins")
    last_time = pygame.time.get_ticks()  # Store the time at the start    # Store the time at the start
    interval = 60000  # 60,000 milliseconds = 1 minute
    if datetime.now().date() != datetime.fromisoformat(data.get("Last Saved DateTime")).date():
        i = 0
    else:
        i = 20 - data.get("Gacha Balls")
    coinNum += int(abs((datetime.now() - datetime.fromisoformat(data.get("Last Saved DateTime"))).total_seconds())/300)
    if coinNum > 20:
        coinNum = 20
    left_pressed = False
    right_pressed = False
    leftbutton1 = pygame.image.load("images/left-button1.png").convert_alpha()
    leftbutton2 = pygame.image.load("images/left-button2.png").convert_alpha()
    rightbutton1 = pygame.image.load("images//right-button1.png").convert_alpha()
    rightbutton2 = pygame.image.load("images//right-button2.png").convert_alpha()

    # Button positions
    left_button_rect = leftbutton1.get_rect(topleft=(50, 575))
    right_button_rect = rightbutton1.get_rect(topleft=(150, 575))
    transparent_surface = pygame.Surface((100, 100))  # Same size as the screen
    transparent_surface.set_alpha(0)
    while running:
        screen.fill((0, 0, 0))  # Clear screen
        screen.blit(background_image, (0, 0))  # Draw background
        font = pygame.font.Font(None, 64)
        text_surface = font.render(str(coinNum) + "x", True, (81, 87, 120))
        
        # Define the text position (center of the screen)
        text_rect = text_surface.get_rect(center=(475, 618))
        
        # Draw the updated text on the screen
        screen.blit(text_surface, text_rect)
        button_rect = draw_button(screen, "Show Prizes", 570, 540, 100, 50, (255, 173, 192), (0, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
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
                    gacha_prizes.append(create_gacha_ball(space))
                    i += 1
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    shuffle_balls(gacha_prizes)
                if event.key == pygame.K_LEFT and claw_state == "idle":  # Only move if in idle state
                    claw_x = max(100, claw_x - claw_speed)  # Stay within bounds
                    left_pressed = True
                if event.key == pygame.K_RIGHT and claw_state == "idle":  # Only move if in idle state
                    claw_x = min(SCREEN_WIDTH - 100, claw_x + claw_speed)  # Stay within bounds
                    right_pressed = True
                if event.key == pygame.K_SPACE and claw_state == "idle":  # Space to activate claw if idle
                    if coinNum > 0:
                        claw_state = "descending"
                        current_frame = 0  # Start close animation
                        coinNum -= 1
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    left_pressed = False
                if event.key == pygame.K_RIGHT:
                    right_pressed = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
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
        if claw_state == "idle":
            if left_pressed:
                screen.blit(leftbutton2, left_button_rect)  # Show pressed image for left button
                claw_x = max(100, claw_x - claw_speed)
            else:
                screen.blit(leftbutton1, left_button_rect)  # Show normal image for left button

            if right_pressed:
                screen.blit(rightbutton2, right_button_rect)  # Show pressed image for right button
                claw_x = min(SCREEN_WIDTH - 100, claw_x + claw_speed)
            else:
                screen.blit(rightbutton1, right_button_rect)  # Show normal im
        else:
            screen.blit(leftbutton1, left_button_rect)
            screen.blit(rightbutton1, right_button_rect)

        # Update claw body position for physics
        claw_body.position = (claw_x, claw_body.position.y)

        # Handle claw descending
        if claw_state == "descending":
            claw_body.position = (claw_x, claw_body.position.y + claw_speed)
            # Check if claw reached target or grabbed something
            if claw_body.position.y >= target_claw_y:
                grabbed_ball = check_claw_grab(claw_shape, gacha_prizes)
                claw_state = "ascending"
                current_frame = 0  # Reset for open animation
                frame_counter += 1
                if frame_counter >= frame_delay:
                    frame_counter = 0
                    current_frame = min(current_frame + 1, len(claw_points_close_list) - 1)
            claw_shape = update_claw_shape(space, claw_body, claw_points_close_list, current_frame)
            
            

        # Handle claw ascending
        elif claw_state == "ascending":
            claw_body.position = (claw_x, claw_body.position.y - claw_speed)
            if grabbed_ball:
                ball_body, _ = grabbed_ball
                ball_body.position = claw_body.position + pymunk.Vec2d(0, 40)  # Offset below claw

            # Reset claw to idle state after ascending
            if claw_body.position.y <= original_claw_y:
                claw_state = "idle"
                current_frame = 0  # Reset animation
                frame_counter = 0
                frame_counter += 1
                if frame_counter >= frame_delay:
                    frame_counter = 0
                    current_frame = min(current_frame + 1, len(claw_points_open_list) - 1)
                if grabbed_ball:
                        # Remove grabbed ball
                        body, shape = grabbed_ball
                        # Build a list of all available prizes from all sections
                        available_prizes = [
                            (main_section, subsection, key)
                            for main_section, subsections in prize_sections.items()
                            for subsection, prizes in subsections.items()
                            for key, prize in prizes.items()
                            if not prize["won"]
                        ]

                        if available_prizes:
                            # Randomly select a prize from the available ones
                            selected_main_section, selected_subsection, prize_key = random.choice(available_prizes)

                            # Mark the prize as won in prize_sections
                            prize_sections[selected_main_section][selected_subsection][prize_key]["won"] = True

                            # Show the prize popup with the prize image
                            prize_image = pygame.image.load(
                                prize_sections[selected_main_section][selected_subsection][prize_key]["image"]
                            ).convert_alpha()
                            show_prize_popup(screen, prize_image)

                        gacha_prizes.remove((body, shape))
                        space.remove(body, shape)
                        grabbed_ball = None
                        # grabbed_ball = None
                        print("Ball grabbed and removed!")
            claw_shape = update_claw_shape(space, claw_body, claw_points_open_list, current_frame)

        # Draw claw
        angle = math.degrees(claw_body.angle)
        claw_image = (
            claw_animation_open[current_frame]
            if claw_state == "ascending"
            else claw_animation_close[current_frame]
        )
        blit_rotate_center(
            screen,
            claw_image,
            (
                claw_body.position.x - claw_image.get_width() // 2,
                claw_body.position.y - claw_image.get_height() // 2,
            ),
            -angle,
        )

        # Draw gacha balls
        for body, shape in gacha_prizes:
            angle = math.degrees(body.angle)
            x, y = body.position
            blit_rotate_center(screen, ball_image, (x - 40, y - 40), -angle)
        current_time = pygame.time.get_ticks()
        # Check if a minute has passed
        if current_time - last_time >= interval:
            coinNum += 1
            # Reset the minute timer
            last_time = current_time
        
        
        # Step the physics simulation
        space.step(1 / FPS)
        pygame.display.flip()  # Update display
        clock.tick(FPS)  # Maintain FPS

    pygame.quit()


# Run the game loop
game_loop()

