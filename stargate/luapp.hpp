#ifndef SG_LUAPP_H
#define SG_LUAPP_H

#include <iostream>
#include <fstream>
#include <string>
#include <boost/utility.hpp>

extern "C" {
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h> 
}

using namespace std;

struct LuaFile
{
   char               *buff;
   ifstream::pos_type  size;
   std::string         file_name;
    
   LuaFile( const std::string & _file_name ) : buff(0), size(0), file_name(_file_name)
   {    
      ifstream lua_file(file_name.c_str(), ios::in | ios::binary | ios::ate );
        
      if (!lua_file.is_open())
      {
         cerr << "Failed to open " << file_name << endl;
         return;
      }
        
      size = lua_file.tellg();
      buff = new char[ size ];
        
      lua_file.seekg(0, ios::beg);
      lua_file.read(buff, size);
      lua_file.close();
   }
    
   ~LuaFile() { delete [] buff; }
};


bool load_file( lua_State *L, const std::string fname, bool exec_on_load = true ) {
   LuaFile f(fname);
   if (!f.buff) return false;
   int err = luaL_loadbuffer(L, f.buff, f.size, fname.c_str());
   if ( err == 0 && exec_on_load )
      err = lua_pcall(L,0,0,0);
   if (err) {
      cerr << "Error executing " << fname << ": " << lua_tostring(L,-1) << endl;
      lua_pop(L,1);
      return false;
   }
   return true;
}

struct LuaGuard : boost::noncopyable
{
   lua_State *L;
    
   operator lua_State *() const { return L; }
    
   LuaGuard()
   {
      L = lua_open();
      luaL_openlibs(L);
   }
    
   ~LuaGuard() { lua_close(L); }
    
    
    
/*
  void pushnil    ()                        { lua_pushnil(L); }
  void pushboolean( bool v )                { lua_pushboolean(L, v ? 1 : 0); }
  void push       ( double v )              { lua_pushnumber(L,v); }
  void push       ( const char * v )        { lua_pushstring(L,v); }
  void push       ( const char * v, int l ) { lua_pushstring(L,v,l); }
    
  bool isboolean (int idx=-1) { return lua_isboolean(idx); }
  bool isnumber  (int idx=-1) { return lua_isnumber(idx); }
  bool isstring  (int idx=-1) { return lua_isstring(idx); }
  bool istable   (int idx=-1) { return lua_istable(idx); }
    
  const char * tostring( int idx = -1 ) { return lua_tostring(L,idx); }
  double       tonumber( int idx = -1 ) { return lua_tonumber(L,idx); }
  int          toint( int idx = -1 ) { return (int) tonumber(idx); }
    
  int strlen( int idx = -1 ) { return lua_strlen(L,idx); }
*/
};





#endif

