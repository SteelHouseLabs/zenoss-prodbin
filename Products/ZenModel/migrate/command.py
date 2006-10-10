__doc__='''

Add zCommandPath and zCommandCycleTime to DeviceClass.

'''
import Migrate

class Commands(Migrate.Step):
    version = 23.0

    def update(self, dmd, oldname, name, default, **kw):
        if dmd.Devices.hasProperty(oldname):
            value = not dmd.Devices.getProperty(oldname)
            dmd.Devices._setProperty(name, value, **kw)
            dmd.Devices._delProperty(oldname)
        elif not dmd.Devices.hasProperty(name):
            dmd.Devices._setProperty(name, default, **kw)
        
    def cutover(self, dmd):
        import os
        self.update(dmd, "zNagiosPath", "zCommandPath",
                    os.path.join(os.environ['ZENHOME'], 'libexec'))
        self.update(dmd, "zNagiosCycleTime", "zCommandCycleTime",
                    60, type='int')

Commands()
