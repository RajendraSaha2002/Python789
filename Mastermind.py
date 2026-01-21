from tkinter import *
from collections import Counter
import random


class MediumLogic:
    def __init__(self):
        # 8 available colors, pick 4 unique for the secret code
        self.colors = ['#270101', '#F08B33', '#776B04', '#F1B848',
                       '#8F715B', '#0486DB', '#C1403D', '#F3D4A0']
        self.secret = []
        pool = self.colors[:]
        while len(self.secret) < 4:
            c = random.choice(pool)
            if c not in self.secret:
                self.secret.append(c)

    @staticmethod
    def compare(guess, secret):
        """
        Return list of hint colors:
        - 'red'   for correct color in correct position
        - 'gray'  for correct color in wrong position (count-limited)
        """
        # Reds
        reds = sum(1 for i in range(4) if guess[i] == secret[i])
        # Count remaining for gray calculation
        secret_rest = Counter(secret[i] for i in range(4) if guess[i] != secret[i])
        guess_rest = Counter(guess[i] for i in range(4) if guess[i] != secret[i])
        grays = sum(min(secret_rest[c], guess_rest[c]) for c in guess_rest)

        return ['red'] * reds + ['gray'] * grays


class MasterMind:
    def __init__(self, root):
        self.root = root
        root.title("MasterMind")
        root.geometry('420x640')

        # Game logic
        self.logic = MediumLogic()
        self.colors = self.logic.colors
        self.secret = self.logic.secret

        # Layout: configure enough rows/cols for board + palette + hints
        for y in range(0, 22):  # 0..21
            Grid.rowconfigure(root, y, weight=1)
        for x in range(0, 12):  # 0..11
            Grid.columnconfigure(root, x, weight=1)

        # Status label
        self.status = Label(root, text="Pick 4 colors per row. Good luck!")
        self.status.grid(row=0, column=0, columnspan=12, pady=(6, 0))

        # Positions and state
        self.cur_row = 20          # start placing from bottom up
        self.start_col = 2         # guess pegs start column
        self.cur_col = self.start_col
        self.hints_col_start = 8   # hints area start column
        self.hint_row = self.cur_row
        self.current_guess = []
        self.game_over = False

        # Draw palette
        self.palette_buttons = []
        c = 0
        for color in self.colors:
            btn = Button(root, bg=color, height=1, width=6, relief="raised",
                         command=lambda col=color: self.place_guess(col))
            btn.grid(row=21, column=c, padx=2, pady=4)
            self.palette_buttons.append(btn)
            c += 1

        # Column headers (optional)
        Label(root, text="Guess").grid(row=1, column=self.start_col, columnspan=4)
        Label(root, text="Hints").grid(row=1, column=self.hints_col_start, columnspan=4)

    def place_guess(self, color):
        if self.game_over:
            return
        if self.cur_row < 2:
            return  # no more rows left

        # Place a colored peg (as a Button for simplicity)
        peg = Button(self.root, bg=color, height=1, width=6, relief="sunken", state="disabled")
        peg.grid(row=self.cur_row, column=self.cur_col, padx=1, pady=1)
        self.current_guess.append(color)
        self.cur_col += 1

        # If 4 pegs placed, evaluate the row
        if len(self.current_guess) == 4:
            self.evaluate_row()

    def evaluate_row(self):
        hints = self.logic.compare(self.current_guess, self.secret)

        # Show hints (left-to-right)
        hcol = self.hints_col_start
        for h in hints:
            hl = Label(self.root, bg=h, width=3, relief="sunken")
            hl.grid(row=self.cur_row, column=hcol, padx=1, pady=1, sticky=E)
            hcol += 1

        # Win check
        if len(hints) == 4 and all(h == 'red' for h in hints):
            self.status.config(text="CONGRATULATIONS! You cracked the code!")
            self.reveal_secret(win=True)
            self.end_game()
            return

        # Prepare next row
        self.current_guess = []
        self.cur_row -= 1
        self.hint_row = self.cur_row
        self.cur_col = self.start_col

        # Lose check (no rows left)
        if self.cur_row < 2:
            self.status.config(text="No more attempts. You lost!")
            self.reveal_secret(win=False)
            self.end_game()

    def end_game(self):
        self.game_over = True
        for b in self.palette_buttons:
            b.config(state=DISABLED)

    def reveal_secret(self, win=False):
        msg = "ANSWER: " if not win else "Code: "
        Label(self.root, text=msg).grid(row=0, column=4, columnspan=2, sticky=E)
        col = 6
        for color in self.secret:
            Button(self.root, bg=color, height=1, width=6, relief="sunken", state="disabled").grid(row=0, column=col)
            col += 1


if __name__ == "__main__":
    master = Tk()
    app = MasterMind(master)
    master.mainloop()