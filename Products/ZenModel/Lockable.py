from Products.ZenRelations import RelationshipBase

UNLOCKED = 0
DELETE_LOCKED = 1
UPDATE_LOCKED = 2

class Lockable:
    
    sendEventOnBlockFlag = False
    modelerLock = UNLOCKED
    
    def getNextLockableParent(self, obj):
        if obj.getPrimaryParent() == self.getDmd():
            return None
        elif isinstance(obj.getPrimaryParent(), Lockable):
            return obj.getPrimaryParent()
        else:
            return self.getNextLockableParent(obj.getPrimaryParent())
    
    def sendEventOnBlock(self):
        if sendEventOnBlockFlag:
            return True
        else:
            lockableParent = self.getNextLockableParent(self)
            if lockableParent:
                return self.getNextLockableParent(self).sendEventOnBlock()
            else:
                return False
                
    def isLockedFromDeletion(self):
        if self.modelerLock == DELETE_LOCKED or self.modelerLock == UPDATE_LOCKED:
            return True
        else:
            lockableParent = self.getNextLockableParent(self)
            if lockableParent:
                return getNextLockableParent(self).isLockedFromDeletion()
            else:
                return False
                
    def isLockedFromUpdates(self):
        if self.modelerLock == UPDATE_LOCKED: 
            return True
        else:
            lockableParent = self.getNextLockableParent(self)
            if lockableParent:
                return getNextLockableParent(self).isLockedFromUpdates()
            else:
                return False
                
    def unlock(self):
        self.modelerLock = UNLOCKED
    
    def lockFromDeletion(self):
        self.modelerLock = DELETE_LOCKED
    
    def lockFromUpdates(self):
        self.modelerLock = UPDATE_LOCKED
    
    def lockStatus(self):
        '''
        if self.modelerLock == DELETE_LOCKED:
            return "Locked from deletion"
        elif self.modelerLock == UPDATE_LOCKED:
            return "Locked from updates and deletion"
        elif isinstance(self.getPrimaryParent(), Lockable):
            return "%s by parent" % self.getPrimaryParent().lockStatus()
        elif self.modelerLock == UNLOCKED:
            return "Unlocked"
        '''
        if self.isLockedFromDeletion():
            return "Locked from deletion"
        elif self.isLockedFromUpdates():
            return "Locked from updates and deletion"
        else:
            return "Unlocked"
            
    def lockWarning(self):
        if self.sendEventOnBlock():
            return "Send event on block"
        else:
            return "Do not send event on block"
            