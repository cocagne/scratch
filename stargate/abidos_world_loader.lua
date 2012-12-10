
local M = {}

local world_def = require "abidos_world_def"
local wrappers  = require "abidos_lua_wrappers"

local TBOOL        = 0
local TINT32       = 1
local TUINT32      = 2
local TINT64       = 3
local TUINT64      = 4
local TFLOAT       = 5
local TDOUBLE      = 6
local TBYTE_STRING = 7
local TUUID        = 8
local TINSTANCE    = 9

local WB_TYPE    = 0
local WB_OBJECT  = 1
local WB_MESSAGE = 2

local wb_types = { boolean = TBOOL,
                   int32   = TINT32,
                   uint32  = TUINT32,
                   int64   = TINT64,
                   uint64  = TUINT64,
                   float   = TFLOAT,
                   double  = TDOUBLE,
                   string  = TBYTE_STRING,
                   uuid    = TUUID }


M.loaded_worlds = {}


-- w = abidos_world_def.World instance
--
local function build_cxx_world( world_name, w )
    local _,t,a,baseclass,type_type,btype,type_id,superclass_id
    local lines = {}

    -- The following table contains entries for every unique DataType:ArraySize pair
    -- used in the world
    local array_tbl = {}
    local arr_id    = #w.types + 1

    for _,t in ipairs(w.types) do
        for _,a in ipairs(t.attributes) do
            if a.array_size then
                local k = a.dtype .. ':' .. tostring(a.array_size)
                if not array_tbl[k] then
                    local atbl = {arr_id, a.dtype, a.array_size}
                    array_tbl[k] = atbl
                    table.insert(array_tbl, atbl)
                    arr_id = arr_id + 1
                end
            end
        end
    end

    abidos_cxx_builder.world_init( world_name, #w.types, #array_tbl, w:get_extra_info() )
    
    for _,t in ipairs(w.types) do
        if t.superclass then
            superclass_id = w.types[ t.superclass ].type_id
        else
            superclass_id = -1
        end

        if t.is_object then
            type_type = WB_OBJECT
        elseif t.is_message then
            type_type = WB_MESSAGE
        else
            type_type = WB_TYPE
        end

        -- This next bit adds each unique, non-low-level datatype to a table. The length
        -- of this table will then indicate how many pointers to other data types this
        -- type will require
        local ntypes = {}
        for _,a in ipairs(t.attributes) do
            if not wb_types[ a.dtype ] then
                if not ntypes[ a.dtype ] then
                    table.insert( ntypes, a.dtype )
                    ntypes[ a.dtype ] = true
                end
            end
        end

        
        abidos_cxx_builder.add_type( t.name, type_type, superclass_id, #t.attributes, #ntypes, t:get_extra_info() )

        
        for _,a in ipairs(t.attributes) do
            type_id = 0
            btype   = wb_types[ a.dtype ]
            btype   = btype or TINSTANCE
            
            if btype == TINSTANCE then
                type_id = w.types[ a.dtype ].type_id
            end

            if a.array_size then
                local k = a.dtype .. ':' .. tostring(a.array_size)
                type_id = array_tbl[k][1]
                btype   = TINSTANCE
            end
            
            abidos_cxx_builder.add_variable( a.name, btype, type_id, a:get_extra_info() )
        end
    end

    local arr, is_basic
    for _,arr in ipairs(array_tbl) do
        is_basic = wb_types[ arr[2] ] ~= nil
        if is_basic then
            btype   = wb_types[ arr[2] ]
            type_id = 0
        else
            btype   = 0
            type_id = w.types[ arr[2] ]
        end
        
        abidos_cxx_builder.add_array( arr[3], btype, type_id, is_basic )
    end

    return abidos_cxx_builder.world_finalize()
end


function M.get_world( world_name )
    return M.loaded_worlds[ world_name ]
end


function M.cxx_load_world( world_name, filename )
    if M.loaded_worlds[ world_name ] then
        print("** RETURNING PRELOADED WORLD: " .. world_name)
        return M.loaded_worlds[ world_name ]._cxx
    else
        print( "***********************************" )
        print( "  LOADING WORLD " .. world_name )
        wd = world_def.load( filename )
        
        w = build_cxx_world( world_name, wd )
        
        print( "World type: " .. type(w) )
        print( "World name: " .. w:getName())
        print( "***********************************" )

        local ww = wrappers.World:new(w, world_name)

        M.loaded_worlds[ world_name ] = ww
                
        return w
    end
end

function M.lua_load_world( world_name )
    return M.loaded_worlds[ world_name ]
end

return M