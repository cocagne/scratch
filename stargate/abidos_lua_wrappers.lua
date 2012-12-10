local M = {}


--------------------------------------------------------------------------------------------
-- World
--
M.World = {}

function M.World:new( cxx_world, world_def )
    o = {}
    setmetatable(o,self)
    self.__index = self

    o.name       = cxx_world:getName()
    o._def       = world_def
    o._cxx       = cxx_world
    
    o.types      = {} 
    o.objects    = {}
    o.messages   = {}
    
    return o
end


function M.World:newInterface( interface_name )
    local wi
    
    wi = M.WorldInterface:new( self, interface_name )
    
    wi._cxx = self._cxx:newInterface( interface_name, wi )

    return wi
end


--------------------------------------------------------------------------------------------
-- WorldInterface
--
M.WorldInterface = {}

function M.WorldInterface:new( world, name )
    o = {}
    setmetatable(o,self)
    self.__index = self

    o.name    = name
    o.world   = world
    o._cxx    = nil
                       
    o.callbacks  = {}  -- Table of tables: index = type_id, val = list of callbacks
                       -- type_id = 0, means callback for all objects
    o.types      = {} 
    o.objects    = {}
    o.messages   = {}
    
    return o
end


function M.WorldInterface:_new_object( cxx_obj )
    --print( "&&&&&&& Lua WorldInterface:_new_object called! Args: ", self, cxx_obj )
    local obj = M.Object:new( cxx_obj )
    self.objects[ obj.uuid ] = obj
    -- TODO: walk the type hierarchy for most specific match
    if self.callbacks[ 0 ] then
        for _,cb in ipairs(self.callbacks[0]) do
            cb( obj )
        end
    end
end

function M.WorldInterface:addCallback( type_id, cb )
    if not self.callbacks[ type_id  ] then
        self.callbacks[ type_id ] = {}
    end
    table.insert(self.callbacks[type_id], cb)
end

function M.WorldInterface:runCallbacks()
    self._cxx:runCallbacks()
end


--------------------------------------------------------------------------------------------
-- Object
--
M.Object = {}

function M.Object:new( cxx_obj )
    o = {}
    setmetatable(o,self)
    self.__index = self

    o._cxx    = cxx_obj

    o.uuid    = cxx_obj:getUUID()
    o.type_id = cxx_obj:getTypeId()
    
    
    return o
end



return M

