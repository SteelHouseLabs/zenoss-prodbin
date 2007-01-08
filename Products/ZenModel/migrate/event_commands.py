__doc__='Add commands to EventManager'

import Migrate

class EventCommands(Migrate.Step):
    version = Migrate.Version(1, 1, 0)
    
    def cutover(self, dmd):
        dmd.Events.createOrganizer("/Status/Web")
        dmd.ZenEventManager.buildRelations()

EventCommands()
