
local M = {}

local current_world = nil

local simple_types = { boolean = true,
                       int32   = true,
                       uint32  = true,
                       int64   = true,
                       uint64  = true,
                       float   = true,
                       double  = true,
                       string  = true,
                       uuid    = true }
                      
local numeric_types = { int32   = true,
                        uint32  = true,
                        int64   = true,
                        uint64  = true,
                        float   = true,
                        double  = true }

local boolean_constants = { ['true']  = 'true',
                            ['True']  = 'true',
                            ['TRUE']  = 'true',
                            [1]       = 'true',
                            ['false'] = 'false',
                            ['False'] = 'false',
                            ['FALSE'] = 'false',
                            [0]       = 'false' }


--------------------------------------------------------------------------------------------
-- World
--
M.World = {}

function M.World:new()
    o = {}
    setmetatable(o,self)
    self.__index = self

    o.name       = ''
    o.types      = {} -- maps type_id & name to Type instance
    o.objects    = {}
    o.messages   = {}
    o.extra_info = nil -- key = value pairs for extra stuff in the world definition file
    
    return o
end

function M.World:add_type( t )
    if self.types[ t.type_id ] then
        error("Duplicate definition of type number: " .. t.type_id)
    end

    if self.types[ t.name ] then
        error("Duplicate definition of type name: " .. t.name)
    end

    t.world = self

    self.types[ t.type_id ] = t
    self.types[ t.name    ] = t

    if t.is_object then
        table.insert(self.objects, t)
        self.objects[ t.name    ] = t
        self.objects[ t.type_id ] = t
    end

    if t.is_message then
        table.insert(self.messages, t)
        self.messages[ t.name    ] = t
        self.messages[ t.type_id ] = t
    end
end

function M.World:get_extra_info()
    return self.extra_info or {}
end

function M.World:print_self()
    local _,t
    for _,t in ipairs(self.types) do
        t:print_self()
    end
end



--------------------------------------------------------------------------------------------
-- Type
--
M.Type = {}

function M.Type:new()
    o = {}
    setmetatable(o,self)
    self.__index = self

    o.name       = ''
    o.type_id    = 0
    o.world      = nil
    
    o.attributes   = {} -- maps attribute_id & name to Attribute instance
    o.next_attr_id = 1

    o.extra_info  = nil -- key = value pairs for extra stuff in the world definition file

    o.description = nil
    o.superclass  = nil
    o.is_object   = false
    o.is_message  = false
    
    return o
end


function M.Type:get_extra_info()
    return self.extra_info or {}
end


function M.Type:get_derivation_level()
    if self.superclass then
        return self.world.types[ self.superclass ]:get_derivation_level() + 1
    else
        return 0
    end
end


function M.Type:add_attribute( a )
    if not a.id then
        a.id = self.next_attr_id
        self.next_attr_id = self.next_attr_id + 1
    end
    if self.attributes[ a.id ] then
        error('Duplicate attribute ID: ' .. a.id)
    end

    if self.attributes[ a.name ] then
        error('Duplicate attribute name: ' .. a.name)
    end

    table.insert(self.attributes, a)
    self.attributes[ a.id   ] = a
    self.attributes[ a.name ] = a
end


function M.Type:print_self()
    local kind = 'Type'
    if self.is_object then
        kind = 'Object'
    elseif self.is_message then
        kind = 'Message'
    end
    local super = ''
    if self.superclass then
        super = ' Superclass: ' .. self.superclass
    end
    print(kind..'  '..self.name..'  type_id:'..self.type_id..super)
    local _,a
    for _,a in ipairs(self.attributes) do
        a:print_self('   ')
    end
end


--------------------------------------------------------------------------------------------
-- Attribute
--
M.Attribute= {}

function M.Attribute:new()
    o = {}
    setmetatable(o,self)
    self.__index = self

    o.id      = nil
    o.dtype   = ''
    
    --[[
    o.array_size  = nil
    o.extra_info  = nil -- key = value pairs for extra stuff in the world definition file
    --]]
    return o
end

function M.Attribute:check_default()

    if self.extra_info and self.extra_info.default then
        local d = self.extra_info.default
        if numeric_types[self.dtype] then
            if d:sub(1,2) == "0x" then
                d = tostring( tonumber(d:sub(3,-1),16) )
            end
            if not tonumber(d) then
                error("Invalid numeric default: " .. d)
            end
            self.extra_info.default = tostring(d)
        end
        if self.dtype == 'boolean' then
            if not boolean_constants[d] then
                error("Invalid boolean default: " .. d)
            end
            self.extra_info.default = boolean_constants[ d ]
        end
    end
end

function M.Attribute:get_extra_info()
    return self.extra_info or {}
end


function M.Attribute:print_self(indent)
    indent = indent or ''
    opt = ''
    if self.array_size then opt = opt .. ' array size = ' .. self.array_size end
    if self.units then opt = opt .. ' units:'..self.units end
    if self.description then opt = opt .. ' description:' .. self.description end
    print(indent..'Attr: '..self.name..' ('..self.dtype..')'..opt)
end

--------------------------------------------------------------------------------------------
-- Helper Functions
--
local function check_required( args, required, kind )
    local _,name
    for _,name in ipairs(required) do
        if not args[name] then
            error("Missing required attribute \'" ..name.. "\' from "..kind.." definition.")
        end
    end
end

local function create_extra_info( args, ignore_map )
    local k,v,xi
    xi = nil
    for k,v in pairs(args) do
        if type(k) == 'string' and not ignore_map[k] then
            if not xi then xi = {} end
            xi[ k ] = v
        end
    end
    return xi
end


local function def_world( args )
    if current_world then 
        error("Only one world definition is permitted") 
    end

    check_required(args, {'name'}, 'World')
    
    current_world = M.World:new()
    current_world.name = args.name

    current_world.extra_info = create_extra_info( args, { name=true } )
    
    if args.version then
        current_world.version = args.version
    end
end


local function add_attr( t, atbl )

    if #atbl < 2 then
        error('Invalid attribute definition. A minimum of name and type is required')
    end

    local a = M.Attribute:new()

    a.name  = atbl[1]
    a.dtype = atbl[2]

    if not simple_types[ a.dtype ] and not current_world.types[ a.dtype ] then
        error('Invalid attribute type: '..a.dtype)
    end

    function opt_copy( attrs )
        local _,n 
        for _,n in ipairs( attrs ) do
            if atbl[n] ~= nil then
                a[n] = atbl[n]
            end
        end
    end

    a.extra_info = create_extra_info( atbl, { name=true, ['type']=true, id=true, array_size=true } )
    
    opt_copy( {'id', 'array_size'} )

    a:check_default()
    
    t:add_attribute( a )
    
end


local function def_type( args, kind )
    kind = kind or 'Type'
    check_required(args, {'name', 'type_id'}, kind)
    local t = M.Type:new()
    t.name       = args.name
    t.type_id    = args.type_id
    t.is_object  = kind == 'Object'
    t.is_message = kind == 'Message'

    --    print('Defining type: '.. t.name .. ' kind = ' .. kind)
    
    if args.superclass then
        t.superclass = args.superclass
    end
    
    t.extra_info = create_extra_info( args, { name=true, superclass=true, type_id=true } )

    local _,atbl

    for _,atbl in ipairs(args) do
        add_attr( t, atbl )
    end

    current_world:add_type( t )
end


local function def_object( args )
    def_type(args, 'Object')
end


local function def_message( args )
    def_type(args, 'Message')
end


function M.load( filename )
    
    assert(not current_world)
    
    local new_world = M.World:new()
    local env = { World   = def_world,
                  Type    = def_type,
                  Object  = def_object,
                  Message = def_message,
                  __index = _G }

    setmetatable(env,env)

    local tenv = getfenv(1)
    setfenv(0,env)
    dofile(filename)
    setfenv(0,tenv)
    
    local tmp = current_world
    current_world = nil
    return tmp
end


return M