#!/usr/bin/python3
"""Generate weave mazes using Kruskal's algorithm.

Weave mazes have passages that can cross over and under each other, but only
in straight lines. This makes them easy to visualize in 2D. This program also
can add extra openings to the maze, changing it from a perfect maze to one
with cycles. This makes the maze "easier" in some sense (lower diameter), but
also prevents right-hand-following from working.
"""

import argparse
import random

class DisjointCell:
    """A single cell in a disjoint-set forest."""
    __slots__ = ("rank", "parent")

    def __init__(self):
        self.rank = 0
        self.parent = self

    def top(self):
        """Return the set this cell belongs to."""
        i = self.parent
        if i != self:
            i = i.top()
            self.parent = i
        return i

    def union(self, other):
        """Union the set of this cell with 'other'."""
        mine = self.top()
        other = other.top()
        if mine.rank >= other.rank:
            other.parent = mine
        else:
            mine.parent = other


def genmaze(options):
    """Generate a maze with the given options.

    Returns a width * height array of bitfields.
    Bit 0 = Passage to the south
    Bit 1 = Passage to the east
    Bit 2 = Weave, vertical on top
    Bit 3 = Weave, horizontal on top

    Not all patterns are valid - the weave bits are mutually exclusive, and also
    imply the first two bits. Also, the edges can't have passages out.
    """
    w = options.width
    h = options.height
    size = w * h
    sets = [DisjointCell() for i in range(size)]
    conn = [0] * size
    rng = random.Random(options.seed)
    # Create a shuffled order of walls to carve
    walls = [i*2 for i in range(w*(h-1))]
    walls += [(y*w + x)*2 + 1 for y in range(h) for x in range(w-1)]
    rng.shuffle(walls)
    # Perform Kruskal's algorithm
    for wall in walls:
        # Make weaves first, possibly several
        while rng.random() < options.weave_fraction:
            x, y = rng.randrange(1, w-1), rng.randrange(1, h-1)
            pos = y * w + x
            # Abort if we have any connections beyond 1 or straight through.
            # This automatically rules out a weave on this square (but not
            # adjacent squares).
            if (conn[pos-1]&2 | conn[pos-w]&1 | conn[pos]) >= 3:
                continue
            # Connect across the weave branches. If there is already a passage in,
            # then the set we need to connect from is the middle instead of the
            # arm. If there is a straight-across, we connect the middle to the
            # middle, which is a no-op.
            cell1 = sets[pos - (1 - (conn[pos-1] & 2) // 2)]
            cell2 = sets[pos + (1 - (conn[pos] & 2) // 2)]
            if cell1 != cell2:
                cell1 = cell1.top()
                cell2 = cell2.top()
                if cell1 == cell2:
                    continue
            cell3 = sets[pos - w * (1 - (conn[pos-w] & 1))]
            cell4 = sets[pos + w * (1 - (conn[pos] & 1))]
            if cell3 != cell4:
                cell3 = cell3.top()
                cell4 = cell4.top()
                if cell3 == cell4:
                    continue
            cell1.union(cell2)
            cell3.union(cell4)
            # Carve the passages.
            conn[pos] = rng.choice([7, 11])
            conn[pos-1] |= 2
            conn[pos-w] |= 1
        pos = wall // 2
        dirr = (wall&1) + 1
        if conn[pos] & dirr:
            continue
        cell1 = sets[pos].top()
        cell2 = sets[pos + (w if dirr == 1 else 1)].top()
        if cell1 == cell2:
            continue
        conn[pos] |= dirr
        cell1.union(cell2)
        y = wall // (w*2)
        x = wall // 2 - y*w
    return conn


def print_maze(conn, width):
    """Print a maze as box drawing characters.

    Assumes entrance/exit at top-left/bottom-right.
    """
    maze_cells = """
┌─┐
└─┘
┌─┐
│ │
┌──
└──
┌──
│ ┌
│ │
└─┘
│ │
│ │
│ └
└──
│ └
│ ┌
──┐
──┘
──┐
┐ │
───
───
───
┐ ┌
┘ │
──┘
┘ │
┐ │
┘ └
───
┘ └
┐ ┌
┤ ├
┤ ├
┴─┴
┬─┬""".strip().split("\n")
    # Collect into pairs
    maze_cells = list(zip(maze_cells[:-1:2], maze_cells[1::2]))
    for y in range(len(conn) // width):
        for row in range(2):
            for x in range(width):
                pos = y * width + x
                left = 0 if x == 0 else (conn[pos-1]&2)
                up = 0 if y == 0 else (conn[pos-width]&1)
                idx = ((left | up)) << 2 | conn[pos]
                if pos == 0:
                    idx |= 4
                elif pos == len(conn) - 1:
                    idx |= 1
                if conn[pos] > 3:
                    idx = 15 + conn[pos] // 4
                print(maze_cells[idx][row], end="")
            print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
        description=__doc__)
    parser.add_argument("--help", action='help', help='show this help message and exit')
    parser.add_argument("-w", "--width", type=int, default=12,
        help="Width of the maze, in passages.")
    parser.add_argument("-h", "--height", type=int, default=12,
        help="Height of the maze, in passages.")
    parser.add_argument("-f", "--weave_fraction", type=float, default=.3,
        help="What proportion of the maze should be weaved. Setting this too "
             "high will cause the weave preprocessing to never terminate!")
    parser.add_argument("-x", "--extra_openings", type=int, default=5,
        help="How many extra openings to add, i.e. how many cycles to form "
             "inside the maze graph.")
    parser.add_argument("-s", "--seed",
        help="The random number seed. If unspecified, urandom() will be used "
             "to generate and print a base64 seed.")
    args = parser.parse_args()

    if not args.seed:
        from os import urandom
        from base64 import b64encode
        seed = b64encode(urandom(12)).decode()
        print("Random seed is: " + seed)
        args.seed = seed

    maze = genmaze(args)
    print_maze(maze, args.width)
