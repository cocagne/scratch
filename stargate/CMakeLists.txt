project(stargate)

cmake_minimum_required( VERSION 2.8 )


include_directories( /home/thomas.cocagne/dhd_tools/include )
link_directories(/home/thomas.cocagne/dhd_tools/lib )

include_directories( /home/thomas.cocagne/tools/include )
link_directories( /home/thomas.cocagne/tools/lib )
      
include_directories(${CMAKE_CURRENT_BINARY_DIR})

set(CMAKE_C_FLAGS -ggdb)
set(CMAKE_CXX_FLAGS -ggdb)

set(LUA_FILES ${CMAKE_SOURCE_DIR}/abidos_world_def.lua 
              ${CMAKE_SOURCE_DIR}/abidos_world_loader.lua
              ${CMAKE_SOURCE_DIR}/abidos_lua_wrappers.lua)
              
set(CXX_LUA ${CMAKE_CURRENT_BINARY_DIR}/abidos_embedded_lua.cpp)

add_custom_command( OUTPUT ${CXX_LUA} PRE_BUILD 
                    COMMAND ${CMAKE_SOURCE_DIR}/lua2cxx abidos_embedded_lua ${LUA_FILES} > ${CXX_LUA}
                    DEPENDS ${LUA_FILES} )

add_library(abidos SHARED ${CXX_LUA}
                     abidos_common.cpp
                     abidos_data.cpp
                     abidos_type_encoding.cpp
                     abidos_world.cpp 
                     abidos_world_builder.cpp
		     abidos_lua.cpp
		     abidos_world_interface.cpp )
                     
target_link_libraries(abidos lua dl boost_thread boost_system)                     


add_executable(ltest test.cpp)
                     
target_link_libraries(ltest abidos)                     


add_library(test_model SHARED test_model.cpp)
target_link_libraries(test_model abidos)

#target_link_libraries(dhd_frontend boost_thread boost_filesystem boost_system ${PROTOBUF_LIBRARY} pthread fuse rt dl ssl)
#target_link_libraries(dhd_backend boost_thread boost_filesystem boost_system ssl ${PROTOBUF_LIBRARY})

