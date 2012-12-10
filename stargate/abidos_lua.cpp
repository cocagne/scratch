#include "abidos_lua.hpp"

#include "world_builder.hpp"

#include "abidos_world.hpp"
#include "abidos_world_builder.hpp"
#include "abidos_world_interface.hpp"
#include "abidos_data.hpp"
#include "abidos_model.hpp"

#ifndef WIN32
#include <dlfcn.h>
#endif


// Initialization function generated by lua2cxx
namespace abidos_embedded_lua { void lua2cxx_init( lua_State * L ); }


namespace abidos
{
// defined in abidos_world_builder.cpp
sg::WorldBuilder * createWorldBuilder();

sg::PWorld load_world( const char * world_name, const char * file_name );

boost::thread_specific_ptr<ThreadSpecificLuaWrapper> g_tssLuaState;

//-----------------------------------------------------------------------------
// Exceptions
//
LoadError::LoadError( const std::string & msg ) :
      AbidosError( msg )
{}

LuaError::LuaError( lua_State *L, std::string prefix ) : AbidosError("")
{
   err_msg = prefix + std::string(lua_tostring(L,-1));
   lua_pop(L,1);
}

//-----------------------------------------------------------------------------
// Thread Specific Lua Wrapper
//
ThreadSpecificLuaWrapper::ThreadSpecificLuaWrapper( lua_State *_L ) :
      L(_L)
{
   if (L)
   {
      bCxxDelete = false;
   }
   else
   {
      L = lua_open();
      luaL_openlibs(L);
      bCxxDelete = true;
   }
}
    
ThreadSpecificLuaWrapper::~ThreadSpecificLuaWrapper()
{
   if (bCxxDelete)
      lua_close(L);
}

//-----------------------------------------------------------------------------
// Lua File Loading
//
char * read_file( std::string file_name, std::size_t *pnNumBytes )
{
   char               *buff = 0;
   ifstream::pos_type  size = 0;

   *pnNumBytes = 0;
   
   ifstream lua_file(file_name.c_str(), ios::in | ios::binary | ios::ate );
        
   if (!lua_file.is_open())
      throw AbidosError( std::string("Failed to open file: ") + file_name );
   
   size = lua_file.tellg();
   buff = new char[ size ];
   
   lua_file.seekg(0, ios::beg);
   lua_file.read(buff, size);
   lua_file.close();

   *pnNumBytes = (std::size_t) size;
   return buff;
}


void loadLuaFile( std::string fname, bool exec_on_load )
{
   char        *fbytes = 0;
   std::size_t  fsize  = 0;

   lua_State *L = g_tssLuaState->L;

   if (!L)
      throw AbidosError("Thread Specific Lua Interpreter not initialied");
   
   fbytes = read_file( fname, &fsize );

   if ( luaL_loadbuffer(L, fbytes, fsize, fname.c_str()) )
   {
      delete [] fbytes;
      throw LuaError(L, std::string("Failed to load file \"") + fname + std::string("\": "));
   }

   delete [] fbytes;
   
   if ( exec_on_load )
   {
      if (lua_pcall(L,0,0,0))
         throw LuaError(L, std::string("Failed to execute file \"") + fname + std::string("\": "));
   }
}



//-----------------------------------------------------------------------------
// Anonymous Namespace For Lua Function & Type Wrappers
//
namespace
{

bool getWrapper( lua_State *L, void *ptr, const char * name, bool do_longjump = true )
{
   lua_pushlightuserdata(L, ptr);
   lua_gettable(L, LUA_REGISTRYINDEX);
   if (!lua_istable(L, -1))
   {
      if ( do_longjump )
         luaL_error(L, "Failed to obtain wrapper object for %s", name);
      else
         return false;
   }
   return true;
}

// Sets the value on the top of the stack to be the wrapper for the
// C++ instance at *ptr
void setWrapper( lua_State *L, void *ptr )
{
   lua_pushlightuserdata(L, (void*) ptr);
   lua_pushvalue(L,-2);
   lua_settable(L, LUA_REGISTRYINDEX);
}


void init_object_wrapper( lua_State *L, const char * szMetaTableName, luaL_Reg * pr )
{
   luaL_newmetatable(L, szMetaTableName);

   lua_pushstring(L, "__index");
   lua_pushvalue(L, -2); // pushes the metatable on the stack
   lua_settable(L, -3);  // metatable.__index = metatable

   while( pr->name )
   {
      lua_pushstring(L, pr->name);
      lua_pushcfunction(L, pr->func);
      lua_settable(L,-3);
      ++pr;
   }
}

//-----------------------------------------------------------------------------
// World & World Interface wrappers
//
int wrap_world( lua_State *L, sg::PWorld world )
{
   void * addr = lua_newuserdata(L, sizeof(sg::PWorld));
   
   new (addr) sg::PWorld( world );

   luaL_getmetatable(L, "abidos.mWorld");
   lua_setmetatable(L, -2);

   return 1; // 1 indicates single return value on the stack
}

sg::PWorld checkWorld( lua_State *L, int index = 1 )
{
   sg::PWorld *p = (sg::PWorld *) luaL_checkudata(L, index, "abidos.mWorld");
   luaL_argcheck(L, p != NULL, index, "`world' expected");
   return *p;
}

int world_setWrapper( lua_State *L )
{
   sg::PWorld p  = checkWorld(L);
   luaL_checktype(L,-1, LUA_TTABLE);

   setWrapper(L, p.get());
   
   return 0;
}

int world_getName( lua_State *L )
{
   sg::PWorld w = checkWorld(L);
   lua_pushstring(L, w->getName());
   return 1;
}

// Prototype
void wi_object_created_cb( lua_State *L, WorldInterface * pwi, sg::PObject obj );


// args: (interface_name, wrapper_table)
int world_newInterface( lua_State *L )
{
   WorldInterface *  pwi    = 0;
   World          *  pw     = dynamic_cast<World *>( checkWorld(L).get() );
   const char     *  szname = luaL_checkstring(L,2);
   luaL_checktype(L,3, LUA_TTABLE);

   if (!pw)
   {
      lua_pushstring(L, "Dynamic cast of World argument to World failed");
      lua_error(L);
   }
   
   void * addr = lua_newuserdata(L, sizeof(sg::PWorldInterface));

   pwi = new WorldInterface( szname, pw );

   // Add global callback for all created objects
   pwi->setNewObjectHandler( 0, boost::bind( wi_object_created_cb, L, pwi, _1 ) );
   
   new (addr) sg::PWorldInterface( pwi );
   
   luaL_getmetatable(L, "abidos.mWorldInterface");
   lua_setmetatable(L, -2);

   lua_pushvalue(L,3);
   setWrapper(L, pwi);

   lua_pop(L,1);

   return 1; // 1 indicates single return value on the stack
}


int world_printTypes( lua_State *L )
{
   sg::PWorld w = checkWorld(L);
   w->printTypes();
   return 0;
}

int world_destructor( lua_State *L )
{
   sg::PWorld *p = (sg::PWorld *) luaL_checkudata(L, 1, "abidos.mWorld");
   if (p)
   {
      std::cerr << "~~~~ Lua World Destructor: " << (*p)->getName() << std::endl;
      p->reset();
   }
   return 0;
}


void init_world_wrapper( lua_State *L )
{
   luaL_Reg funcs[] = { {"getName",      world_getName      },
                        {"printTypes",   world_printTypes   },
                        {"newInterface", world_newInterface },
                        {"_setWrapper",  world_setWrapper   },
                        {"__gc",         world_destructor   },
                        {0,0} };
   init_object_wrapper( L, "abidos.mWorld", funcs );
}


//-----------------------------------------------------------------------------
// World Interface Wrapper
//
// Note: Creation of new interfaces is done via World:newInterface()
//

// Prototype
int wrap_object( lua_State *L, sg::PObject pi );

WorldInterface * checkWorldInterface( lua_State *L, int index=1 )
{
   sg::PWorldInterface *p = (sg::PWorldInterface *) luaL_checkudata(L, index, "abidos.mWorldInterface");
   luaL_argcheck(L, p != NULL, index, "`WorldInterface' expected");
   return static_cast<WorldInterface *>( (*p).get() );
}

void wi_object_created_cb( lua_State *L, WorldInterface * pwi, sg::PObject obj )
{
   //cerr << "%%% LUA CALLBACK FUNCTION: " << pwi->getName() << "  Obj: " << obj.get() << " iface: " << pwi << endl;

   if ( !getWrapper(L, pwi, "WorldInterface") )
   {
      cerr << "%%% Failed to get WorldInterface Wrapper for  " << pwi->getName() << endl;
      return;
   }

   lua_pushstring(L, "_new_object"); 
   lua_gettable(L, -2);              
   
   if( !lua_isfunction(L, -1) )
   {
      cerr << "%%% Failed to get _new_object function from WorldInteface wrapper" << endl;
      lua_pop(L, 1);
      return;
   }
   
   lua_pushvalue(L, -2);  
   wrap_object( L, obj ); 

   // [-4] = <WorldInterfaceWrapper>
   // [-3] = <function>
   // [-2] = <WorldIntefaceWrapper>
   // [-1] = <object wrapper>

   if( lua_pcall(L, 2, 0, 0) != 0 )
   {
      cerr << "%%% WorldInterface wrapper _new_object call failed: " << lua_tostring(L,-1) << endl;
      lua_pop(L,2); // remove err message and WorldInterface wrapper
      return;
   }

   // [-1] = <WorldInterfaceWrapper>
   lua_pop(L,1); 
}


int wi_createObject( lua_State *L )
{
   WorldInterface * pwi    = checkWorldInterface(L);
   int              typeId = luaL_checknumber(L,2);

   wrap_object(L, pwi->createObject(typeId));
   
   std::cerr << "Create object called with ID: " << typeId << endl;
   
   return 1;
}


int wi_runCallbacks( lua_State *L )
{
   WorldInterface * pwi    = checkWorldInterface(L);

   pwi->runCallbacks();
   
   return 1;
}


int wi_destructor( lua_State *L )
{
   sg::PWorldInterface *p = (sg::PWorldInterface *) luaL_checkudata(L, 1, "abidos.mWorldInterface");
   if (p)
   {
      std::cerr << "~~~~ Lua World Interface Destructor " << std::endl;
      p->reset();
   }
   return 0;
}


void init_world_interface_wrapper( lua_State *L )
{
   luaL_Reg funcs[] = { {"createObject", wi_createObject },
                        {"runCallbacks", wi_runCallbacks },
                        {"__gc",         wi_destructor   },
                        {0,0} };
   init_object_wrapper( L, "abidos.mWorldInterface", funcs );
}


//-----------------------------------------------------------------------------
// Object Wrapper
//
// Note: Creation of new interfaces is done via World:createObject()
//
int wrap_object( lua_State *L, sg::PObject po )
{
   void * addr = lua_newuserdata(L, sizeof(sg::PObject));
   
   new (addr) sg::PObject( po );

   luaL_getmetatable(L, "abidos.mObject");
   lua_setmetatable(L, -2);

   return 1; // 1 indicates single return value on the stack
}


Object * checkObject( lua_State *L, int index=1 )
{
   sg::PObject *p = (sg::PObject *) luaL_checkudata(L, index, "abidos.mObject");
   luaL_argcheck(L, p != NULL, index, "`Object' expected");
   return static_cast<Object *>( (*p).get() );
}

// Prototype
int wrap_instance( lua_State *L, sg::PInstance pi );

int ob_getInstance( lua_State *L )
{
   Object * po = checkObject(L);

   wrap_instance(L, po->getInstance());
   
   return 1;
}


int ob_getTypeId( lua_State *L )
{
   Object * po = checkObject(L);

   lua_pushinteger(L, po->getTypeId());
   
   return 1;
}

int ob_getUUID( lua_State *L )
{
   Object * po = checkObject(L);

   const UUID * u = static_cast< const UUID * >(po->getUUID());
   lua_pushlstring(L, (const char *)u->uid.data, u->uid.size());
      
   return 1;
}


int ob_destructor( lua_State *L )
{
   sg::PObject *p = (sg::PObject *) luaL_checkudata(L, 1, "abidos.mObject");
   if (p)
   {
      std::cerr << "~~~~ Lua Object Instance Destructor " << std::endl;
      p->reset();
   }
   return 0;
}


void init_object_wrapper( lua_State *L )
{
   luaL_Reg funcs[] = { {"getInstance", ob_getInstance },
                        {"getUUID",     ob_getUUID     },
                        {"getTypeId",   ob_getTypeId   },
                        {"__gc",        ob_destructor  },
                        {0,0} };
   init_object_wrapper( L, "abidos.mObject", funcs );
}


//-----------------------------------------------------------------------------
// Instance Wrapper
//
//
int wrap_instance( lua_State *L, sg::PInstance pi )
{
   void * addr = lua_newuserdata(L, sizeof(sg::PInstance));
   
   new (addr) sg::PInstance( pi );

   luaL_getmetatable(L, "abidos.mInstance");
   lua_setmetatable(L, -2);

   return 1; // 1 indicates single return value on the stack
}

Instance * checkInstance( lua_State *L, int index=1 )
{
   sg::PInstance *p = (sg::PInstance *) luaL_checkudata(L, index, "abidos.mInstance");
   luaL_argcheck(L, p != NULL, index, "`Instance' expected");
   return static_cast<Instance *>( (*p).get() );
}

int in_get( lua_State *L )
{
   Instance * pi    = checkInstance(L);
   int        deriv = luaL_checknumber(L,2);
   int        attr  = luaL_checknumber(L,3);
   int        atyp  = luaL_checknumber(L,4);

   sg::AttributeID aid(deriv, attr);

   switch( atyp )
   {
    case sg::TBOOL        : lua_pushboolean(L, pi->getBoolean(aid) ? 1 : 0 ); break;
    case sg::TINT32       : lua_pushnumber(L, pi->getInt32(aid)); break;
    case sg::TUINT32      : lua_pushnumber(L, pi->getUInt32(aid)); break;
    case sg::TINT64       : lua_pushnumber(L, pi->getInt64(aid)); break;
    case sg::TUINT64      : lua_pushnumber(L, pi->getUInt64(aid)); break;
    case sg::TFLOAT       : lua_pushnumber(L, pi->getFloat(aid)); break;
    case sg::TDOUBLE      : lua_pushnumber(L, pi->getDouble(aid)); break;
    case sg::TBYTE_STRING :
    {
       const ByteString * bs = pi->getByteString(aid);
       lua_pushlstring(L, (const char *)bs->data(), bs->length());
    }
       break;
    case sg::TUUID        :
    {
       const UUID * u = pi->getUUID(aid);
       lua_pushlstring(L, (const char *)u->uid.data, u->uid.size());
    }
       break;
    case sg::TINSTANCE    :
       wrap_instance(L, pi->getInstance(aid));
       break;
    default:
       lua_pushstring(L, "Invalid data type");
       lua_error(L);
   }
   
   return 1;
}


int in_set( lua_State *L )
{
   Instance * pi    = checkInstance(L);
   int        deriv = luaL_checknumber(L,2);
   int        attr  = luaL_checknumber(L,3);
   int        atyp  = luaL_checknumber(L,4);
   
   sg::AttributeID aid(deriv, attr);

   switch( atyp )
   {
    case sg::TBOOL        : pi->setBoolean(aid, lua_toboolean(L,5)); break;
    case sg::TINT32       : pi->setInt32(aid,   lua_tonumber(L,5)); break;
    case sg::TUINT32      : pi->setUInt32(aid,  lua_tonumber(L,5)); break;
    case sg::TINT64       : pi->setInt64(aid,   lua_tonumber(L,5)); break;
    case sg::TUINT64      : pi->setUInt64(aid,  lua_tonumber(L,5)); break;
    case sg::TFLOAT       : pi->setFloat(aid,   lua_tonumber(L,5)); break;
    case sg::TDOUBLE      : pi->setDouble(aid,  lua_tonumber(L,5)); break;
    case sg::TBYTE_STRING :
    {
       std::size_t len = 0;
       const char *data = lua_tolstring(L, 5, &len);
       pi->setByteString(aid, (const uint8_t*)data, len);
    }
       break;
    case sg::TUUID        :
       lua_pushstring(L, "TODO: UUID assignment support");
       lua_error(L);
       break;
    case sg::TINSTANCE    :
       lua_pushstring(L, "TODO: Instance assignment support");
       lua_error(L);
       break;
    default:
       lua_pushstring(L, "Invalid data type");
       lua_error(L);
   }
   
   return 0;
}


int in_destructor( lua_State *L )
{
   sg::PInstance *p = (sg::PInstance *) luaL_checkudata(L, 1, "abidos.mInstance");
   if (p)
   {
      std::cerr << "~~~~ Lua Instance Destructor " << std::endl;
      p->reset();
   }
   return 0;
}


void init_instance_wrapper( lua_State *L )
{
   luaL_Reg funcs[] = { {"get",          in_get          },
                        {"set",          in_set          },
                        {"__gc",         in_destructor   },
                        {0,0} };
   init_object_wrapper( L, "abidos.mInstance", funcs );
}


//-----------------------------------------------------------------------------
// Model Wrapper
//
//
int wrap_model( lua_State *L, AbidosModel * pm )
{
   AbidosModel **lm = (AbidosModel **) lua_newuserdata(L, sizeof(AbidosModel *));

   *lm = pm;

   luaL_getmetatable(L, "abidos.mModel");
   lua_setmetatable(L, -2);

   return 1; // 1 indicates single return value on the stack
}


AbidosModel * checkModel( lua_State *L, int index=1 )
{
   AbidosModel **p = (AbidosModel **) luaL_checkudata(L, index, "abidos.mModel");
   luaL_argcheck(L, p != NULL, index, "`Object' expected");
   return *p;
}


int mdl_tick( lua_State *L )
{
   AbidosModel * pm = checkModel(L);

   pm->tick();
   
   return 0;
}


int mdl_destructor( lua_State *L )
{
   AbidosModel *p = (AbidosModel *) luaL_checkudata(L, 1, "abidos.mModel");
   if (p)
   {
      std::cerr << "~~~~ Lua AbidosModel Destructor (skipping delete) " << std::endl;
      
   }
   return 0;
}


void init_model_wrapper( lua_State *L )
{
   luaL_Reg funcs[] = { {"tick", mdl_tick },
                        {"__gc", mdl_destructor  },
                        {0,0} };
   init_object_wrapper( L, "abidos.mModel", funcs );
}


//-----------------------------------------------------------------------------
// World Builder
//
char gRegistryKey; // run-time address used as index to LuaRegistry


class AbidosBuildError : public sg::BuildError
{
   std::string err_msg;
      
  public:
   AbidosBuildError( const std::string & msg ) : err_msg(msg) {}
      
   ~AbidosBuildError() throw() {}
      
   virtual const char * what() const throw()
   {
      return err_msg.c_str();
   }
};

   
struct CState
{
   sg::WorldBuilder * pbuilder;
   sg::PWorld         world;
      
   CState() : pbuilder( createWorldBuilder() ), world(0)
   {}
       
   ~CState() 
   {
      delete pbuilder;
   }
};
         
void registerCS( lua_State *L, CState * pcs )
{
   lua_pushlightuserdata(L, &gRegistryKey);
   lua_pushlightuserdata(L, pcs);
   lua_settable(L, LUA_REGISTRYINDEX);
}

void unregisterCS( lua_State *L )
{
   lua_pushlightuserdata(L, &gRegistryKey);
   lua_pushnil(L);
   lua_settable(L, LUA_REGISTRYINDEX);
}
   
CState * getCS( lua_State *L )
{
   lua_pushlightuserdata(L, &gRegistryKey);
   lua_gettable(L, LUA_REGISTRYINDEX);
   CState *cs = 0;
   
   if ( lua_islightuserdata(L, -1) )
   {
      cs = (CState *) lua_topointer(L, -1);
      lua_pop(L,1);
   }
       
   if (!cs)
      throw AbidosBuildError("CState not initialized");
       
   return cs;
}
   
// Extra info table must be at index idx
void fill_xi( lua_State *L, int idx, sg::WorldBuilder::ExtraInfo & xi )
{
   lua_pushnil(L); // using nil for the first key
   while (lua_next(L,idx) != 0)
   {
      if (!lua_isstring(L,-1) || !lua_isstring(L,-2))
         throw AbidosBuildError("Invalid entry in ExtraInfo table. Only strings are allowed");
      xi[ lua_tostring(L,-2) ] = lua_tostring(L,-1);
      lua_pop(L,1);
   }
}
   
   
int wb_init( lua_State *L )
{
   bool         err        = false;
   const char * name       = luaL_checkstring(L,1);
   int          num_types  = luaL_checknumber(L,2);
   int          num_arrays = luaL_checknumber(L,3);
   luaL_checktype(L,4, LUA_TTABLE);
       
   try
   {
      sg::WorldBuilder::ExtraInfo xi;
           
      fill_xi( L, 4, xi );
       
      getCS(L)->pbuilder->init( name, num_types, num_arrays, xi );
   }
   catch ( sg::BuildError & e )
   {
      err = true;
      lua_pushstring(L, e.what());
   }
   if (err)
      lua_error(L);
       
   return 0;
}
   
    
int wb_addType( lua_State *L )
{
   bool         err            = false;
   const char * name           = luaL_checkstring(L,1);
   int          type_type      = (int) luaL_checknumber(L,2);
   int          superclass_id  = (int) luaL_checknumber(L,3);
   int          num_attributes = (int) luaL_checknumber(L,4);
   int          num_types      = (int) luaL_checknumber(L,5);
   luaL_checktype(L,6, LUA_TTABLE);
       
   try
   {
      sg::WorldBuilder::ExtraInfo xi;
           
      fill_xi( L, 6, xi );
       
      getCS(L)->pbuilder->addType( name, (sg::TypeType) type_type, superclass_id, num_attributes, num_types, xi );
   }
   catch ( sg::BuildError & e )
   {
      err = true;
      lua_pushstring(L, e.what());
   }
   if (err)
      lua_error(L);
       
   return 0;
}
   
int wb_addArray( lua_State *L )
{
   bool         err         = false;
   int          array_size  = (int) luaL_checknumber(L,1);
   int          btype       = (int) luaL_checknumber(L,2);
   int          type_id     = (int) luaL_checknumber(L,3);
   bool         is_basic    = false;
       
   if (lua_gettop(L) >= 4)
      is_basic = lua_toboolean(L,4) == 1;
       
   try
   {       
      getCS(L)->pbuilder->addArray( array_size, (sg::BasicType) btype, type_id, is_basic );
   }
   catch ( sg::BuildError & e )
   {
      err = true;
      lua_pushstring(L, e.what());
   }
   if (err)
      lua_error(L);
       
   return 0;
}
      
int wb_addVariable( lua_State *L )
{
   bool         err        = false;
   const char * name       = luaL_checkstring(L,1);
   int          btype      = (int) luaL_checknumber(L,2);
   int          type_id    = (int) luaL_checknumber(L,3);
   luaL_checktype(L,4, LUA_TTABLE);
       
   try
   {
      sg::WorldBuilder::ExtraInfo xi;
           
      fill_xi( L, 4, xi );
       
      getCS(L)->pbuilder->addVariable( name, (sg::BasicType)btype, type_id, xi );
   }
   catch ( sg::BuildError & e )
   {
      err = true;
      lua_pushstring(L, e.what());
   }
   if (err)
      lua_error(L);
       
   return 0;
}
   
int wb_finalize( lua_State *L )
{
   bool err = false;
       
   try
   {
      CState * cs = getCS(L);
           
      cs->world = cs->pbuilder->finalize();

      return wrap_world( L, cs->world );
   }
   catch ( sg::BuildError & e )
   {
      err = true;
      lua_pushstring(L, e.what());
   }
   if (err)
      lua_error(L);
       
   return 0;
}

// Called from Lua to call the C++ function that turns around
// and calls Lua. We need to do this to ensure that the CState
// is registered for all of the world creation functions
int lua_load_world( lua_State *L )
{
   bool err = false;
   
   const char * world_name  = luaL_checkstring(L,1);
   const char * file_name   = luaL_checkstring(L,2);

   try
   {
      load_world( world_name, file_name );

      lua_getglobal(L, "abidos_world_loader");
      lua_pushstring(L, "lua_load_world");
      lua_gettable(L, -2);

      lua_pushstring(L, world_name);

      int err = lua_pcall(L, 1, 1, 0);

      if ( err )
         throw LoadError( lua_tostring(L,-1) );

      cerr << "****************** RETURN OK ******************" << endl;
      lua_pushvalue(L,-1);
      return 1;
   }
   catch(std::exception & e)
   {
      lua_pushstring(L, e.what());
      err = true;
   }

   cerr << "^^^^^^^^^^^^^^ ACK ^^^^^^^^^^^^^^^^^^^" << endl;
   
   if (err)
      lua_error(L);

   return 0;
}



//--------------------------------------------------------------------------
// Begin Dynamic Module Loading
//
typedef AbidosModel * (*ModelCreationFunc)( World * );

int lua_create_model( lua_State *L )
{
   typedef std::map<std::string, ModelCreationFunc> PluginMap;
   
   static PluginMap plugins;
   
   ModelCreationFunc   func      = 0;
   sg::PWorld          world     = checkWorld(L, 1);
   const char        * dll_name  = luaL_checkstring(L, 2);
   const char        * func_name = luaL_checkstring(L, 3);
   const char        * dll_err   = 0;

   // Anonymous block to prevent longjumping over C++ constructors/destructors
   {
      std::string std_dll_name = dll_name;
   
      PluginMap::iterator i = plugins.find( std_dll_name );

      if ( i == plugins.end() )
      {
         plugins[ std_dll_name ] = 0;
         
#ifndef WIN32
         void * h = dlopen( dll_name, RTLD_NOW | RTLD_LOCAL );
         if (!h)
            dll_err = dlerror();
         else
         {
            func = (ModelCreationFunc) dlsym(h, func_name);

            if (!func)
               dll_err = dlerror();
            else
               plugins[ std_dll_name ] = func;
         }
#endif
         
      }

      func = plugins[ std_dll_name ];
   }

   if (dll_err)
      luaL_error(L, "DLL error encountered while loading module %s: %s", dll_name, dll_err);
   
   if (!func)
      luaL_error(L, "Failed to load model %s", dll_name);
   
   wrap_model( L, func( static_cast<World *>( world.get() ) ) );

   return 1;
}
// End Dynamic Module Loading
//-------------------------------------------------------------------------
     
} // end anonymous namespace


void load_abidos_bindings( lua_State *L )
{
   luaL_Reg builder[] = { {"world_init",     wb_init       },
                          {"add_type",       wb_addType    },
                          {"add_array",      wb_addArray   },
                          {"add_variable",   wb_addVariable},
                          {"world_finalize", wb_finalize   },
                          {0,0} };

   // If called from Lua, the TSS wrapper will not be set. Do so now.
   if (!g_tssLuaState.get())
   {
      g_tssLuaState.reset( new ThreadSpecificLuaWrapper(L) );
   }
   
   luaL_register(L, "abidos_cxx_builder", builder);

   init_world_wrapper( L );
   init_world_interface_wrapper( L );
   init_object_wrapper( L );
   init_instance_wrapper( L );
   init_model_wrapper( L );

   //-------------------------------------------------------
   // Embedded Lua Code
   //
   abidos_embedded_lua::lua2cxx_init(L);
    
   luaL_dostring(L, "abidos_world_loader = require \"abidos_world_loader\"");

   //-------------------------------------------------------
   // Global "abidos" table. Mostly for Lua convenience
   //
   lua_newtable(L);

   lua_pushstring(L, "load_world");
   lua_pushcfunction(L, lua_load_world);
   lua_settable(L, -3);

   lua_pushstring(L, "create_model");
   lua_pushcfunction(L, lua_create_model);
   lua_settable(L, -3);

   lua_setglobal(L, "abidos");
}


sg::PWorld load_world( const char * world_name, const char * file_name )
{
   if (!g_tssLuaState.get())
   {
      g_tssLuaState.reset( new ThreadSpecificLuaWrapper );

      load_abidos_bindings( g_tssLuaState->L );
   }
   
   lua_State *L = g_tssLuaState->L;
    
   CState cs;
    
   registerCS(L, &cs);
    
   lua_getglobal(L, "abidos_world_loader");
   lua_pushstring(L, "cxx_load_world");
   lua_gettable(L, -2);

   lua_pushstring(L, world_name);
   lua_pushstring(L, file_name);

   int err = lua_pcall(L, 2, 1, 0);

   unregisterCS(L);
    
   if ( err )
      throw LoadError( lua_tostring(L,-1) );
        
   if ( !cs.world )
      throw LoadError( "Unknown load error!" );

   sg::PWorld *p = (sg::PWorld *) luaL_checkudata(L, -1, "abidos.mWorld");

   lua_pop(L, 1);

   if (!p)
      throw LoadError("Failed to obtain World instance from world loader");

   cerr << "++++++++ World Loaded: " << world_name << endl;

   return *p;
}

} // end namespace abidos


extern "C"
{
   int luaopen_abidos( lua_State *L )
   {
      abidos::load_abidos_bindings( L );
      return 1;
   }
}









