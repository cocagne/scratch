
#ifndef ABIDOS_WORLD_LOADER_H
#define ABIDOS_WORLD_LOADER_H

#include <iostream>
#include <stdexcept>
#include <fstream>
#include <string>
#include <boost/utility.hpp>
#include <boost/unordered_map.hpp>
#include <boost/thread/tss.hpp>

extern "C"
{
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h> 
}


#include "abidos_common.hpp"


namespace abidos
{

class LoadError : public AbidosError
{
  public:
        
   LoadError( const std::string & msg );
};


// The constructor for this class pops the error message
// off the top of the lua stack, adds the prefix (if any),
// and uses the result as the message for what()
class LuaError : public AbidosError
{
  public:
   LuaError( lua_State *L, std::string prefix = "" );
};


struct ThreadSpecificLuaWrapper : boost::noncopyable
{
   lua_State *L;
   bool       bCxxDelete; // true if C++ created the lua_State
    
   operator lua_State *() const { return L; }
    
   ThreadSpecificLuaWrapper( lua_State *_L = 0 );
   ~ThreadSpecificLuaWrapper();
};


// Holds a pointer to the Lua interpreter for the current thread. This
// will hold a NULL pointer until explicitly initialized by either C++
// or Lua.
extern boost::thread_specific_ptr<ThreadSpecificLuaWrapper> g_tssLuaState;



// Causes the thread-specific Lua interpreter to load the specified
// file. Throws AbidosError on error.
void loadLuaFile( std::string fname, bool exec_on_load = true );


} // end namespace abidos

#endif

