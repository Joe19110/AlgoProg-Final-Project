import pymunk
import random
class GachaBall:
    # Constants declaration
    SPAWN_X_RANGE = (29, 30)
    SPAWN_Y = 150
    RADIUS = 35
    MASS = 1
    ELASTICITY = 0.8
    FRICTION = 0.5
    COLLISION_TYPE = 1

    def __init__(self, space):
        self.space = space

        # Use constants for initialization
        spawn_x = random.randint(*self.SPAWN_X_RANGE)
        spawn_y = self.SPAWN_Y

        # Create the body and shape
        self.body = pymunk.Body(self.MASS, pymunk.moment_for_circle(self.MASS, 0, self.RADIUS))
        self.body.position = spawn_x, spawn_y
        self.shape = pymunk.Circle(self.body, self.RADIUS)
        self.shape.elasticity = self.ELASTICITY
        self.shape.friction = self.FRICTION
        self.shape.collision_type = self.COLLISION_TYPE

        # Add the body and shape to the space
        self.space.add(self.body, self.shape)

    def get_body_and_shape(self): # Returns the pymunk body and shape of the gacha ball
        return self.body, self.shape
    
    def shuffle(self, intensity=500): # Apply random forces to shuffle the gacha ball
        # Generate random force components
        force_x = random.uniform(-intensity, intensity)
        force_y = random.uniform(-intensity, intensity)
        
        # Apply the impulse to the ball's body
        self.body.apply_impulse_at_local_point((force_x, force_y))
