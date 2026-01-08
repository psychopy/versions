from pathlib import Path
import wx

from psychopy.app.themes import icons


class DeviceImageList(wx.ImageList):
    """
    Image list of device icons, allowing indices to be accessed by the device class
    """
    def __init__(
            self, 
            width=16, 
            height=16, 
            mask=True, 
            initialCount=1
        ):
        # initialise as normal
        wx.ImageList.__init__(
            self, 
            width=width, 
            height=height, 
            mask=mask, 
            initialCount=initialCount
        )
        # create index cache
        self.indices = {}

    def getIcon(self, device):
        """
        Get the corresponding icon index of the icon for a given device based on its class.

        Parameters
        ----------
        device : psychopy.experiment.devices.DeviceBackend or type
            Device object (or device class) to get the icon for
        """
        # get device class
        if not isinstance(device, type):
            device = type(device)
        # try to get from indices cache
        if device in self.indices:
            return self.indices[device]
        # get icon file
        file = device.getIconFile()
        # load icon from file (if exists)
        if file and Path(file).is_file():
            bmp = icons.BaseIcon.resizeBitmap(
                wx.Bitmap(str(device.getIconFile())),
                size=self.GetSize()
            )
            i = self.Add(bmp)
            # cache and return
            self.indices[device] = i

            return i
        
        # all else fails, use blank
        return -1
        