from math import sin, cos

class ScreenPoint:
    def __init__(self, ndc, cart):
        self.ndc = ndc
        self.cart = cart

    def serialize(self):
        return [
            self.ndc,
            self.cart
        ]

    @classmethod
    def deserialize(cls, data):
        return ScreenPoint(
            ndc=data[0],
            cart=data[1]
        )

    def __str__(self):
        return f'({str(self.ndc)}, {str(self.cart)})'

class ScreenTriangle:
    def __init__(self, pa, pb, pc):
        self.pa = pa
        self.pb = pb
        self.pc = pc

    def serialize(self):
        return [
            self.pa.serialize(),
            self.pb.serialize(),
            self.pc.serialize()
        ]

    @classmethod
    def deserialize(cls, data):
        return ScreenTriangle(
            pa=ScreenPoint.deserialize(data[0]),
            pb=ScreenPoint.deserialize(data[1]),
            pc=ScreenPoint.deserialize(data[2])
        )

    def __str__(self):
        return f'({str(self.pa)}, {str(self.pb)}, {str(self.pc)})'

class Screen:
    """
    Class representing the configuration of a single screen used in the display of stimuli.
    Parameters such as screen coordinates and the ID # are represented.
    """

    def __init__(self, width=None, height=None, rotation=None, offset=None, server_number=None, id=None,
                 fullscreen=None, vsync=None, square_side=None, square_loc=None, name=None, tri_list=None):
        """
        :param width: width of the screen (meters)
        :param height: height of the screen (meters)
        :param rotation: rotation of the screen about the z axis (radians).  a value of zero corresponds to the screen
        width being aligned along the x axis.
        :param offset: position of the center of the screen (3-vector in meters).
        :param server_number: ID # of the X server
        :param id: ID # of the screen
        :param fullscreen: Boolean.  If True, display stimulus fullscreen (default).  Otherwise, display stimulus
        in a window.
        :param vsync: Boolean.  If True, lock the framerate to the redraw rate of the screen.
        :param square_side: Length of photodiode synchronization square (meters).
        :param square_loc: Location of photodiode synchronization square (one of 'll', 'lr', 'ul', 'ur' or a tuple of (x,y))
        :param name: descriptive name to associate with this screen
        :param tri_list: list of triangular patches defining the screen geometry.  this is a list of ScreenTriangles.
        if the triangle list is not specified, then one is constructed automatically using rotation and offset.
        """

        # Set defaults for MacBook Pro (Retina, 15-inch, Mid 2015)

        width = width or 0.332
        height = height or 0.207
        rotation = rotation or 0.0
        offset = offset or (0.0, 0.3, 0.0)
        server_number = server_number or 0
        id = id or 0
        fullscreen = fullscreen or True
        vsync = vsync or True
        square_side = square_side or 2e-2
        square_loc = square_loc or 'll'
        name = name or ('Screen' + str(id))

        # Construct a default triangle list if needed
        if tri_list is None:
            ll = self.screen_corner(name='ll', width=width, height=height, offset=offset, rotation=rotation)
            lr = self.screen_corner(name='lr', width=width, height=height, offset=offset, rotation=rotation)
            ur = self.screen_corner(name='ur', width=width, height=height, offset=offset, rotation=rotation)
            ul = self.screen_corner(name='ul', width=width, height=height, offset=offset, rotation=rotation)

            tri_list = self.quad_to_tri_list(ll, lr, ur, ul)

        # save the triangle list
        self.tri_list = tri_list

        # Save settings
        self.width = width
        self.height = height
        self.id = id
        self.server_number = server_number
        self.fullscreen = fullscreen
        self.vsync = vsync
        self.square_side = square_side
        self.square_loc = square_loc
        self.name = name

    @classmethod
    def name_to_ndc(cls, name):
        return {
            'll': (-1, -1),
            'lr': (+1, -1),
            'ur': (+1, +1),
            'ul': (-1, +1)
        }[name.lower()]

    @classmethod
    def screen_corner(cls, name, width, height, offset, rotation):
        # figure out the NDC coordinates of the named screen corner
        ndc = cls.name_to_ndc(name)

        # compute the 3D cartesian coordinates of the screen corner
        cart_x = 0.5 * width  * cos(rotation) * ndc[0] + offset[0]
        cart_y = 0.5 * width  * sin(rotation) * ndc[0] + offset[1]
        cart_z = 0.5 * height                 * ndc[1] + offset[2]

        # return the 3D coordinate
        return ScreenPoint(ndc=ndc, cart=(cart_x, cart_y, cart_z))

    @classmethod
    def quad_to_tri_list(cls, p1, p2, p3, p4):
        # convert points to ScreenPoints if necessary
        p1 = p1 if isinstance(p1, ScreenPoint) else ScreenPoint.deserialize(p1)
        p2 = p2 if isinstance(p2, ScreenPoint) else ScreenPoint.deserialize(p2)
        p3 = p3 if isinstance(p3, ScreenPoint) else ScreenPoint.deserialize(p3)
        p4 = p4 if isinstance(p4, ScreenPoint) else ScreenPoint.deserialize(p4)

        # create a mesh consisting of two triangles
        return [ScreenTriangle(p1, p2, p4), ScreenTriangle(p2, p3, p4)]

    def serialize(self):
        # get all variables needed to reconstruct the screen object
        vars = ['width', 'height', 'id', 'server_number', 'fullscreen', 'vsync', 'square_side', 'square_loc', 'name']
        data = {var: getattr(self, var) for var in vars}

        # special handling for tri_list since it could contain numpy values
        data['tri_list'] = [tri.serialize() for tri in self.tri_list]

        return data

    @classmethod
    def deserialize(cls, data):
        # start building up the argument list to instantiate a screen
        kwargs = data.copy()

        # do some post-processing as necessary
        kwargs['tri_list'] = [ScreenTriangle.deserialize(tri) for tri in kwargs['tri_list']]

        return Screen(**kwargs)

def main():
    screen = Screen(offset=(0.0, +0.3, 0.0), rotation=0)

if __name__ == '__main__':
    main()
