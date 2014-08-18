
RED = "red"
BLACK = "black"

players = [BLACK, RED]
opponent = {BLACK: RED, RED: BLACK}


class ChessException(Exception):

    """The base exception type for the chess game."""

    def __init__(self, message):
        Exception.__init__(self, message)


class InvalidMoveException(ChessException):

    """Represents when an attempted move is invalid."""

    def __init__(self, message):
        ChessException.__init__(self, message)


class InvalidPlacementException(ChessException):

    """Represents an invalid placement of a piece on the board."""

    def __init__(self, message):
        ChessException.__init__(self, message)


class Piece():

    def __init__(self, player):
        if player not in [BLACK, RED]:
            raise ChessException("invalid player %s" % player)
        self.player = player
        self.king = False
        self.board = None
        self.location = None


class Board:

    def __init__(self, dim=8):
        """Create initial game state for normal checkers game."""
        self.dim = dim
        self._neutral_rows = 2
        self._usable_positions = set([(x, y) for y in xrange(0, self.dim) for x in xrange((y + 1) % 2, self.dim, 2)])

        # Pre-compute valid moves
        self._moves = {BLACK: {}, RED: {}}
        self._king_moves = {}
        self._jumps = {BLACK: {}, RED: {}}
        self._king_jumps = {}
        self._captures = {}
        self._init_moves()

        # Mutable data
        self._player_pieces = {BLACK: set(), RED: set()}
        self._loc_pieces = {}

    def _init_moves(self):

        for pos in self.usable_positions():

            pos_x, pos_y = pos

            # Initialize sets for position
            for player in [RED, BLACK]:
                self._moves[player][pos] = set()
                self._jumps[player][pos] = set()
            self._king_moves[pos] = set()
            self._king_jumps[pos] = set()

            # compute valid moves, jumps and captures for normal pieces by player
            for player, mov_off_y, jmp_off_y in [(BLACK, 1, 2), (RED, -1, -2)]:
                for mov_off_x, jmp_off_x in [(-1, -2), (1, 2)]:
                    mov_loc, jmp_loc = (pos_x + mov_off_x, pos_y + mov_off_y), (pos_x + jmp_off_x, pos_y + jmp_off_y)
                    if mov_loc in self.usable_positions():
                        self._moves[player][pos].add(mov_loc)
                    if jmp_loc in self.usable_positions():
                        self._jumps[player][pos].add(jmp_loc)
                        self._captures[(pos, jmp_loc)] = mov_loc

            self._king_moves[pos] = self._moves[BLACK][pos] | self._moves[RED][pos]
            self._king_jumps[pos] = self._jumps[BLACK][pos] | self._jumps[RED][pos]

    def add_piece(self, piece, location):
        """Adds a new Piece to this board. Raises a ChessException if placement is invalid."""
        if not isinstance(piece, Piece):
            raise ChessException('can only add Pieces')
        if not self._valid_placement(piece, location):
            raise InvalidPlacementException('can not place piece at %s' % location)
        piece.board = self
        piece.location = location
        self._player_pieces[piece.player].add(piece)

    def _valid_placement(self, piece, location):
        """Returns true if the specified piece can be placed at the specified location."""
        return location in self._usable_positions and not self[location]

    def start_positions(self):
        """Returns a list of (player,x,y) tuples for start positions"""
        black_positions = [(BLACK, x, y) for (x, y) in self._usable_positions if y < self._player_rows()]
        red_positions = [(RED, x, y) for (x, y) in self._usable_positions if y >= self.dim - self._player_rows()]
        return black_positions + red_positions

    def usable_positions(self):
        """Returns a generator for positions on the board that a piece can occupy."""
        return self._usable_positions

    def _player_rows(self):
        """Returns the number of rows a player controls at game start"""
        return (self.dim - self._neutral_rows) / 2

    def __iter__(self):
        """Allows iteration over the entire set of pieces as tuples (player, x, y)"""
        for player in [BLACK, RED]:
            for piece in self._player_pieces[player]:
                yield piece

    def __getitem__(self, loc):
        """Returns the piece occupying the position specified as a tuple (x,y)"""
        if not loc in self._loc_pieces:
            return None
        return self._loc_pieces[loc]

    def __setitem__(self, loc, piece):
        """Sets the piece occupying the position specified by the tuple (x,y)
        to the specified player"""
        self.move(piece.location, loc)

    def winner(self):
        """Returns the player that has won the game or None if no winner."""
        num_black, num_red = len(self._player_pieces[BLACK]), len(self._player_pieces[RED])
        if num_black and not num_red:
            return BLACK
        elif num_red and not num_black:
            return RED
        else:
            return None

    def _valid_move(self, source, target):
        """Returns whether the move from source to target is a valid move."""

        # Not valid move if the source isn't occupied or target is occupied
        if not self[source] or self[target]:
            return False

        piece = self[source]
        player = piece.player
        moves, jumps = self._moves[player], self._jumps[player]
        capture = self._captures[(source, target)]

        if piece.king:
            moves, jumps = self._king_moves, self._king_jumps

        if target in moves[source]:
            return True
        elif target in jumps[source] and self[capture].player == opponent[player]:
            return True

        return False

    def _move_and_capture(self, source, target):
        """Remove the captured piece and return location, or None if not a capture. Should have already validated as
        valid move with _valid_move before calling this."""
        result = None
        piece = self[source]
        player = piece.player
        capture = self._captures[(source, target)]
        moves, jumps = self._moves[player], self._jumps[player]
        if piece.king:
            moves, jumps = self._king_moves, self._king_jumps
        if target in jumps[source]:  # Handle a capture
            captured_piece = self[capture]
            self._player_pieces[captured_piece.player].remove(captured_piece)  # Remove piece from player
            self._loc_pieces.pop(capture)  # Remove captured piece from board
            captured_piece.location = None  # Captured piece will no longer have a location
            result = captured_piece
        # Move piece to target destination
        self._loc_pieces.pop(source, None)  # Remove piece from original location
        self._loc_pieces[target] = piece
        piece.location = target
        return result

    def move(self, source, target):
        """Moves the piece at source position to target and returns None or the location of a captured piece.
        It throws a InvalidMoveError if the move is not valid."""
        if not self._valid_move():
            raise InvalidMoveException("invalid move from %s to %s" % (source, target))
        return self._move_and_capture(source, target)

    def turn_over(self, player):
        """Returns whether the player's turn is over. This can be used to determine whether to allow multiple
        consecutive turns, such as when jumping multiple pieces."""
        return True

    def __repr__(self):
        """Returns the board representation."""
        result = ""
        for y in xrange(self.dim):
            for x in xrange(self.dim):
                if self[(x, y)] == BLACK:
                    result += 'B'
                elif self[(x,y)] == RED:
                    result += 'R'
                else:
                    result += '*'
            result += '\n'
        return result
