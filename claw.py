
import pymunk
import random
class Claw:
    ORIGINAL_Y = 210
    TARGET_Y = 450
    SPEED = 5
    GRAB_RADIUS = 40
    GRAB_CHANCE = 1
    
    def __init__(self, screen_width, space):
        """Initializes the claw object with animation frames, physics space, and claw properties."""
        self.x = screen_width // 2  # Initial claw X position
        self.body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)  # Initialize pymunk body
        self.body.position = (self.x, self.ORIGINAL_Y)  # Initial claw position
        self.state = "idle"
        self.space = space  # Pymunk space
        self.current_frame = 0  # Track current frame in animation
        self.frame_delay = 5  # Delay before switching to the next frame
        self.frame_counter = 0  # Counter to track frame delays
        self.grabbed_ball = None
        self.shape = None
    
    def descend(self, gacha_prizes, claw_points_close_list):
        self.body.position = (self.x, self.body.position.y + self.SPEED)
            # Check if claw reached target or grabbed something
        if self.body.position.y >= self.TARGET_Y:
            self.grabbed_ball = self.check_grab(gacha_prizes)
            self.state = "ascending"
            self.frame_counter = 0
            self.frame_counter += 1
            if self.frame_counter >= self.frame_delay:
                self.frame_counter = 0
                self.current_frame = min(self.current_frame + 1, len(claw_points_close_list) - 1)
        self.shape = self.update_claw_shape(claw_points_close_list)
    def ascend(self, gacha_prizes, claw_points_open_list):
        flag = False
        self.body.position = (self.x, self.body.position.y - self.SPEED)
        if self.grabbed_ball:
            ball_body, _ = self.grabbed_ball.get_body_and_shape()
            ball_body.position = self.body.position + pymunk.Vec2d(0, 40)  # Offset below claw

        # Reset claw to idle state after ascending
        if self.body.position.y <= self.ORIGINAL_Y:
            self.state = "idle"
            self.current_frame = 0  # Reset animation
            self.frame_counter = 1
            if self.frame_counter >= self.frame_delay:
                self.frame_counter = 0
                self.current_frame = min(self.current_frame + 1, len(claw_points_open_list) - 1)
            if self.grabbed_ball:
                    # Build a list of all available prizes from all sections
                    flag = True
                    gacha_prizes.remove(self.grabbed_ball)
                    self.space.remove(self.grabbed_ball.body, self.grabbed_ball.shape)
                    self.grabbed_ball = None
                    print("Ball grabbed and removed!")
        self.shape = self.update_claw_shape(claw_points_open_list)
        return flag
    def check_grab(self, gacha_prizes):
        for gacha_ball in gacha_prizes:
            body = gacha_ball.body
            # Check distance between the claw's center and the prize's center
            claw_pos = self.shape.body.position
            prize_pos = body.position
            distance = (claw_pos - prize_pos).length  # Vector distance
            if distance <= self.GRAB_RADIUS:  # Check if within grab radius
                if random.random() <= self.GRAB_CHANCE:  # Check grab chance
                    print("Ball grabbed!")
                    return gacha_ball  # Return grabbed ball
        return None
    def update_claw_shape(self, claw_points_list):
        """Update the claw shape based on the current animation frame."""
        # Remove the old shapes from the body and the space
        for shape in self.body.shapes:
            self.space.remove(shape)
        
        # Add the body to the space (if not already added)
        if self.body not in self.space.bodies:
            self.space.add(self.body)

        # Create a new claw shape
        new_claw_points = claw_points_list[self.current_frame]
        self.shape = pymunk.Poly(self.body, new_claw_points)
        self.shape.elasticity = 0.4
        self.shape.friction = 0.5

        # Add the new shape to the space
        self.space.add(self.shape)

        return self.shape

# Usage example:
# Assuming you have a `screen_width`, `space`, and `gacha_prizes` for your game.
# claw = Claw(screen_width=800, space=your_pymunk_space)
# claw.move_claw(speed=5)  # Move the claw towards the target Y position
# grabbed_ball = claw.check_grab(gacha_prizes)
