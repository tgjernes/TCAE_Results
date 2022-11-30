import sys
from os import path, walk
from tkinter.filedialog import askopenfilename

import matplotlib
import numpy as np
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout

matplotlib.use('Qt5Agg')

from PyQt6 import QtCore, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from TCAE_Results_UI import Ui_MainWindow


# Class to subclass QWidget to create a figure and a navigation toolbar
class MplWidget(QWidget):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        QWidget.__init__(self)
        self.setLayout(QVBoxLayout())
        self.canvas = MplCanvas(self, width, height, dpi)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.canvas)


# Class to subclass FigureCanvasQTAgg to easily put it in the GUI
class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        # self.axes = fig.add_subplot(111)
        FigureCanvasQTAgg.__init__(self, fig)
        self.setParent(parent)
        # self.plot()

        # self.fig.plot()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        resid_fig = self.ui.resids_plot.canvas.figure
        ax = resid_fig.add_subplot(111)
        ax.set_xlabel('Timesteps')
        ax.set_ylabel('Residuals')
        ax.grid(which='major')
        ax.grid(which='minor', color='0.9')
        resid_fig.set_tight_layout(True)

        # Load TCAE file to grab/analyze results
        self.ui.pb_load.clicked.connect(self.load_data)
        # sc = self.ui.mons_plot
        # ax0 = sc.canvas.figure.add_subplot(311)
        # ax1 = sc.canvas.figure.add_subplot(312)
        # ax2 = sc.canvas.figure.add_subplot(313)
        # ax0.plot([0, 1, 2, 3, 4], [10, 1, 20, 3, 40])

    def load_data(self):
        # Load TCAE file
        fn = askopenfilename(title='Select the .tcae file for the run you want to analyze',
                             filetypes=[('TCAE files', '*tcae')])
        if not fn:
            return

        with open(fn, 'r') as f:
            tcae_file = f.readlines()

        # Get RPM
        rpm = 0
        for line in tcae_file:
            if line:
                if 'angularVelocity' in line:
                    rpm = line.split('"')[1]
                    break
        if 'RPM' in rpm:
            rpm = float(rpm.split('_')[0])

        # Files & paths for data
        resids_fn = path.join(path.dirname(fn), r'TCFD/logRun/all.log')  # Location of file containing residuals
        mons_path = path.join(path.dirname(fn), r'TCFD/postProcessing/efficiency-0')  # Path where monitors are located
        if not path.isdir(mons_path):  # Check that monitors path exists
            print('Path does not exist:\n%s' % mons_path)
            return
        speedlines = next(walk(mons_path))[1]  # Determine # of separate simulations run in this path
        mons_fn = []
        mons_final_fn = []
        for speedline in speedlines:
            mons_fn.append(
                path.join(mons_path, speedline, 'efficiency.csv'))  # List of CSV files containing all simulation data
            mons_final_fn.append(
                path.join(mons_path, speedline, 'efficiency-final.csv'))  # List of CSV files containing final results

        # Grab/plot residual data
        self.process_resids(resids_fn)

    def process_resids(self, fn):
        # Read residual data
        with open(fn, 'r') as log:
            log_data = log.readlines()

        # Initialize lists
        time = []
        Ux = []
        Uy = []
        Uz = []
        p = []
        omega = []
        k = []

        # Grab residual data from the log
        # cnt_smooth = 0
        cnt_time = 0
        try:
            ind_iter = []
            for i in range(len(log_data)):
                # if 'SmoothSolver' in log_data[i]:
                #     cnt_smooth += 1
                #     if 'Time = ' in log_data[i - 2]:
                #         cnt_time += 1
                #         time.append(int(log_data[i - 2].split()[2]))
                #         ind_iter.append(i)
                if 'Time = ' in log_data[i] and 'Time' in log_data[i][:4]:
                    cnt_time += 1
                    time.append(int(log_data[i].split()[2]))
                    ind_iter.append(i)

            print('Time actual length: %d' % len(time))
            print('ind_iter length: %d' % len(ind_iter))

            max_diff = np.max(np.diff(ind_iter))
            ind_iter.append(ind_iter[-1]+max_diff)
            print('ind_iter new length: %d' % len(ind_iter))
            for j in range(len(ind_iter)-1):
                text_block = log_data[ind_iter[j]:ind_iter[j+1]]
                flag = 0
                for line in text_block:
                    if 'Ux' in line and 'Solver' in line:
                        Ux.append(float(line.split()[7].split(',')[0]))
                        flag += 1
                        if flag > 1:
                            print(ind_iter[j])
                            print(log_data[ind_iter[j]])
                            print(line)
                    elif 'Uy' in line and 'Solver' in line:
                        Uy.append(float(line.split()[7].split(',')[0]))
                    elif 'Uz' in line and 'Solver' in line:
                        Uz.append(float(line.split()[7].split(',')[0]))
                    elif 'omega' in line and 'Solver' in line:
                        omega.append(float(line.split()[7].split(',')[0]))
                    elif 'k, Initial' in line and 'Solver' in line:
                        k.append(float(line.split()[7].split(',')[0]))
                    elif 'GAMG' in line:
                        p.append(float(line.split()[7].split(',')[0]))
            print('j: %d' % j)
        except:
            print('Failed to read residuals from log file')
            print('Failed on line %d' % i)
            print(log_data[i])
            return

        print('log_data length: %d' % len(log_data))
        # print('Smooth length: %d' % cnt_smooth)
        print('Time length: %d' % cnt_time)
        print('Ux length: %d' % len(Ux))
        print('k length: %d' % len(k))

        if len(time) > len(k):
            time = time[:len(k)]
            Ux = Ux[:len(k)]
            Uy = Uy[:len(k)]
            Uz = Uz[:len(k)]
            p = p[:len(k)]
            omega = omega[:len(k)]

        iter_true = range(1, len(time) + 1)

        names = ['Ux', 'Uy', 'Uz', 'p', 'omega', 'k']
        fig = self.ui.resids_plot.canvas.figure
        ax = self.ui.resids_plot.canvas.figure.axes[0]

        Ux_plot = ax.plot(iter_true,Ux,label=names[0])
        Uy_plot = ax.plot(iter_true,Uy,label=names[1])
        Uz_plot = ax.plot(iter_true,Uz,label=names[2])
        p_plot = ax.plot(iter_true,p,label=names[3])
        omega_plot = ax.plot(iter_true,omega,label=names[4])
        k_plot = ax.plot(iter_true,k,label=names[5])
        lines = [Ux_plot, Uy_plot, Uz_plot, p_plot, omega_plot, k_plot]
        ax.set_xlim(0,iter_true[-1])
        ax.set_yscale('log')
        ax.set_ylim(1e-5, 1)
        fig.legend()
        fig.canvas.draw_idle()

        annot = ax.annotate("", xy=(0, 0), xytext=(3, 3), textcoords="offset points", bbox=dict(boxstyle="round", fc="w"))
        annot.set_visible(False)
        fig.canvas.mpl_connect("motion_notify_event", lambda event: self.hover(event, fig))

    def hover(self, event, fig):
        ax = fig.axes[0]
        annot = ax.texts[0]
        vis = annot.get_visible()

        if event.inaxes == ax:
            for line in ax.lines:
                cont, ind = line.contains(event)
                if cont:
                    # print(line.get_label())
                    # self.update_annot(line, ind)
                    x, y = line.get_data()
                    annot.xy = (x[ind["ind"][0]], y[ind["ind"][0]])
                    text = line.get_label()
                    annot.set_text(text)
                    annot.get_bbox_patch().set_alpha(0.4)
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                else:
                    if vis:
                        annot.set_visible(False)
                        fig.canvas.draw_idle()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    win = MainWindow()
    win.show()

    sys.exit(app.exec())
