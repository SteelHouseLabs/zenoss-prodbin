
import Zope
Zope.startup()
from Products.ZenModel.IpInterface import manage_addIpInterface

class PerfTest:

    def __init__(self, app, nints):
        self.dc = app.zport.dmd.Devices
        self.nints = nints

    def create(self):
        device = self.getdev()
        for i in range(self.nints):
            intname = "hme%03d" % i
            manage_addIpInterface(device.interfaces, intname)

    def testints(self):
        for i in range(self.nints):
            intname = "tint%03d" % i
            manage_addIpInterface(self.dc, intname)


    def linkints(self):
        device =  self.getdev()
        for i in range(self.nints):
            intname = "tint%03d" % i
            intobj = self.dc._getOb(intname)
            device.addRelation('interfaces', intobj)


    def delints(self):
        for i in range(self.nints):
            intname = "tint%03d" % i
            self.dc._delObject(intname)


    def rcall(self):
        device = self.getdev()
        for int in device.interfaces():
            n = int.id


    def objvall(self):
        device = self.getdev()
        for int in device.interfaces.objectValuesAll():
            n = int.id


    def objv(self):
        device = self.getdev()
        for int in device.interfaces.objectValues():
            n = int.id


    def deldev(self):
        self.dc._delObject('testdev')
        

    def getdev(self):
        device = self.dc._getOb('testdev', None)
        if not device:
            device = self.dc.createInstance('testdev')
        return device


app = Zope.app()
pt = PerfTest(app, 1000)
