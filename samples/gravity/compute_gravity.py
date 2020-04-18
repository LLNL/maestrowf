from argparse import ArgumentParser

def setup_argparse():
    parser = ArgumentParser(
        prog="compute_gravity",
        description="Simple computation of the force between two bodies")
    parser.add_argument("-m1", "--mass1", type=float,
                        help="Mass of celestial body 1.")
    parser.add_argument("-m2", "--mass2", type=float,
                        help="Mass of celestial body 2.")
    parser.add_argument("-d1", "--dist1", type=float,
                        help="Distance of celestial body 1 from the Sun.")
    parser.add_argument("-d2", "--dist2", type=float,
                        help="Distance of celestial body 2 from the Sun.")
    parser.add_argument("-g", "--gravconst", type=float,
                        help="The gravitational constant")

    return parser

def main():
    parser = setup_argparse()
    args = parser.parse_args()

    g = args.gravconst
    m1 = args.mass1
    m2 = args.mass2
    d1 = args.dist1
    d2 = args.dist2

    r = d2 - d1
    g_force = (g * m1 * m2) / (r**2)

    print(f"----------- MASSES -----------\nmass1 = {m1}\nmass2 = {m2}")
    print(f"---------- DISTANCE ----------\ndist1 = {d1}\ndist2 = {d2}")
    print(f"---------- THE MATH ----------\nradius = {r}\nforce = {g_force}")
    print(f"------------------------------\nThe Force is strong with this one.")


if __name__ == "__main__":
    main()