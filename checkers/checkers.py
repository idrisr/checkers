#!/usr/bin/env python
#
# Clare's Checkers
# A simple checkers game
#
# Released under the GNU General Public License

import os
import sys
import logging as log
import pygame
from pygame.sprite import Sprite, RenderUpdates, GroupSingle
from pygame.constants import QUIT, MOUSEBUTTONDOWN, MOUSEBUTTONUP
from pygame.time import Clock
from internals import Board, Piece, RED, BLACK, InvalidMoveException

BROWN = (143, 96, 40)
WHITE = (255, 255, 255)
TILE_WIDTH = 75
BORDER_WIDTH = 50
BOARD_DIM = 8
SCREEN_RES = (650, 650)
ORIGIN = (0, 0)


class ImageLoader:

    """Loads image resources."""

    def __init__(self):
        pass

    @staticmethod
    def load_img(name, color_key=None):
        """ Load image and return image object"""
        fullname = os.path.join('../images', name)
        log.debug('loading: %s', fullname)
        try:
            image = pygame.image.load(fullname)
            if color_key:
                image.set_colorkey(color_key)   # make all brown transparent
            if image.get_alpha() is None:
                image = image.convert()
            else:
                image = image.convert_alpha()
            return image, image.get_rect()
        except pygame.error, message:
            log.exception('failed to load image %s: %s', fullname, message)
            raise SystemExit


class PieceSprite(Piece, Sprite):

    """A sprite for a single piece."""

    def __init__(self, player):
        Sprite.__init__(self)
        Piece.__init__(self, player)
        screen = pygame.display.get_surface()
        self.area = screen.get_rect()
        if player == RED:
            self.image, self.rect = ImageLoader.load_img('red-piece.png', BROWN)
        elif player == BLACK:
            self.image, self.rect = ImageLoader.load_img('black-piece.png', BROWN)
        else:
            print 'Invalid player name: ', player
            raise SystemExit
        self.player = player
        self.type = "man"

    def update_from_board(self):

        if self.king and self.type != "king":
            # This needs to happen before the rect update below because rect is replaced by image load
            self.type = "king"
            if self.player == RED:
                self.image, self.rect = ImageLoader.load_img('red-piece-king.png', BROWN)
            elif self.player == BLACK:
                self.image, self.rect = ImageLoader.load_img('black-piece-king.png', BROWN)

        self.rect.centerx = TILE_WIDTH * self.location[0] + (TILE_WIDTH / 2) + (BORDER_WIDTH / 2)
        self.rect.centery = TILE_WIDTH * self.location[1] + (TILE_WIDTH / 2) + (BORDER_WIDTH / 2)

    def update(self, position):
        self.rect.centerx, self.rect.centery = position


class SquareSprite(Sprite):

    """A sprite abstraction for game board spaces."""

    def __init__(self, initial_position, color, row, col):
        Sprite.__init__(self)
        screen = pygame.display.get_surface()
        self.area = screen.get_rect()
        self.color = color
        self.row = row
        self.col = col
        if color == "brown":
            self.image, self.rect = ImageLoader.load_img('brown-space.png')
        elif color == "tan":
            self.image, self.rect = ImageLoader.load_img('tan-space.png')
        else:
            print 'Invalid space color: ', color
            raise SystemExit
        self.rect.topleft = initial_position


class Game:

    def __init__(self, title='Checkers', log_level=log.INFO, show_fps=False):
        log.basicConfig(level=log_level)
        self.show_fps = show_fps
        self.window_title = title
        self.game = Board(BOARD_DIM)
        # Initialize Game Groups
        self.brown_spaces = RenderUpdates()
        self.pieces = RenderUpdates()
        self.piece_selected = GroupSingle()
        self.space_selected = GroupSingle()
        self.current_piece_position = ORIGIN
        self.screen = None
        self.fps_clock = None
        self.font = None
        self.font_rect = None
        self.background = None
        self.background_rect = None
        self.fps_text = None
        self.fps_rect = None
        self.winner_text = None
        self.winner_rect = None

    def _board_setup(self, **kwargs):
        """ initialize board state """
        brown_spaces = kwargs.get('brown_spaces')
        for col, row in self.game.usable_positions():
            loc = TILE_WIDTH * col + (BORDER_WIDTH / 2), TILE_WIDTH * row + (BORDER_WIDTH / 2)
            brown_spaces.add(SquareSprite(loc, "brown", row, col))

    def _screen_init(self):
        """ Initialise screen """
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_RES)
        pygame.display.set_caption(self.window_title)
        return self.screen

    def _get_background(self):
        result = pygame.Surface(self.screen.get_size())
        (bg_img, bg_rect) = ImageLoader.load_img('marble-board.jpg')
        result.blit(bg_img, bg_rect)
        return result.convert(), bg_rect

    def _get_fps_text(self):
        fps_text = self.font.render("%4.1f fps" % self.fps_clock.get_fps(), True, WHITE)
        rect = fps_text.get_rect()
        rect.right, rect.bottom = self.background_rect.right, self.background_rect.bottom
        return fps_text, rect

    def _draw_fps(self):
        if self.show_fps:
            self.fps_text, self.fps_rect = self._get_fps_text()
            self.screen.blit(self.fps_text, self.fps_rect)

    def _clear_fps(self):
        if self.show_fps:
            self.screen.blit(self.background, self.fps_rect, area=self.fps_rect)

    def _clear_items(self):
        self._clear_winner()
        self._clear_fps()
        self.piece_selected.clear(self.screen, self.background)
        self.pieces.clear(self.screen, self.background)

    def _draw_winner(self):
        winner = self.game.winner()
        if winner:
            self.winner_text = self.font.render("%s wins!" % winner.title(), True, WHITE)
            winner_rect = self.winner_text.get_rect()
            winner_rect.centerx = self.background.get_rect().centerx
            winner_rect.top = 100
            self.winner_rect = winner_rect
            self.screen.blit(self.winner_text, winner_rect)

    def _clear_winner(self):
        winner = self.game.winner()
        if winner:
            self.screen.blit(self.background, self.winner_rect, area=self.winner_rect)

    def _quit(self):
        log.debug('quitting')
        sys.exit()

    def _select_piece(self, event):
        # select the piece by seeing if the piece collides with cursor
        self.piece_selected.add(piece for piece in self.pieces if piece.rect.collidepoint(event.pos))
        # Capture piece's original position (at center) to determine move on drop
        if len(self.piece_selected) > 0:
            # Assumed: starting a move
            pygame.event.set_grab(True)
            self.pieces.remove(self.piece_selected)
            self.current_piece_position = (self.piece_selected.sprite.rect.centerx,
                                           self.piece_selected.sprite.rect.centery)
            log.debug('grabbing input, picked up piece at %s', self.current_piece_position)

    def _drag_piece(self):
        #  Until button is let go, move the piece with the mouse position
        self.piece_selected.update(pygame.mouse.get_pos())
        log.debug('updated piece to %s', pygame.mouse.get_pos())

    def _drop_piece(self, event):
        if pygame.event.get_grab():
            pygame.event.set_grab(False)
            log.debug('releasing input')

            # center the piece on the valid space; if it is not touching a space, return it to its original position
            self.space_selected.add(space for space in self.brown_spaces
                                    if space.rect.collidepoint(event.pos))

            if self.piece_selected and self.space_selected:
                log.debug('dropped a piece')
                piece, space = self.piece_selected.sprite, self.space_selected.sprite
                try:
                    captured = self.game.move(piece.location, (space.col, space.row))
                    if captured:
                        self.pieces.remove(captured)
                except InvalidMoveException as ce:
                    log.debug(ce)
                log.debug("%s", str(self.game))

            self.piece_selected.sprite.update_from_board()

            # Add piece back to stationary set
            self.pieces.add(self.piece_selected)

            # clean up for the next selected piece
            self.piece_selected.empty()
            self.space_selected.empty()

    def _draw_items(self):
        self.pieces.draw(self.screen)
        self.piece_selected.draw(self.screen)
        self._draw_winner()
        self._draw_fps()


    def run(self):

        log.debug('starting game')

        log.debug('initializing screen')
        self.screen = self._screen_init()

        log.debug('getting font')
        self.font = pygame.font.Font(None, 36)

        log.debug('loading background')
        self.background, self.background_rect= self._get_background()

        log.debug('building initial game board')
        self._board_setup(brown_spaces=self.brown_spaces)

        log.debug('initializing game pieces')
        for player, x, y in self.game.start_positions():
            new_piece = PieceSprite(player)
            self.game.add_piece(new_piece, (x, y))
            new_piece.update_from_board()
            self.pieces.add(new_piece)

        log.debug('drawing initial content to screen')
        self.screen.blit(self.background, ORIGIN)
        pygame.display.flip()

        self.piece_selected = GroupSingle()
        self.space_selected = GroupSingle()
        self.current_piece_position = ORIGIN

        self.fps_clock = Clock()

        self._draw_fps()

        # Event loop
        while True:

            self._clear_items()

            for event in pygame.event.get():

                if event.type == QUIT:
                    self._quit()

                if event.type == MOUSEBUTTONDOWN:     # select a piece
                    log.debug('mouse pressed')
                    self._select_piece(event)

                if event.type == MOUSEBUTTONUP:     # let go of a piece
                    log.debug('mouse released')
                    self._drop_piece(event)

                if pygame.event.get_grab():          # drag selected piece around
                    log.debug('dragging')
                    self._drag_piece()

            self._draw_items()

            self.fps_clock.tick(60)  # Waits to maintain 60 fps

            # TODO: Use display.update instead
            pygame.display.flip()

if __name__ == '__main__':
    Game().run()
