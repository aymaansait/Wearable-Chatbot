import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets


class Oscilloscope:

    def __init__(self, sample_rate=16000):

        self.sample_rate = sample_rate

        self.window_size = sample_rate // 2      # 0.5 second display

        self.buffer = np.zeros(
            self.window_size,
            dtype=np.int32
        )

        self.app = QtWidgets.QApplication.instance()

        if self.app is None:
            self.app = QtWidgets.QApplication([])

        self.window = pg.GraphicsLayoutWidget(
            title="Wearable Chatbot Audio Studio"
        )

        self.plot = self.window.addPlot()

        self.plot.setLabel("left", "Amplitude")

        self.plot.setLabel("bottom", "Samples")

        self.plot.showGrid(x=True, y=True)

        self.curve = self.plot.plot(
            pen='y'
        )

        self.window.show()

    def on_audio_frame(self, samples):

        n = len(samples)

        self.buffer = np.roll(
            self.buffer,
            -n
        )

        self.buffer[-n:] = samples

        self.curve.setData(self.buffer)

        self.app.processEvents()