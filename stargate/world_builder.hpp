#ifndef SG_WORLD_BUILDER_H
#define SG_WORLD_BUILDER_H

#include <exception>
#include <string>
#include <map>

#include "world_interface.hpp"

namespace sg
{
   
class BuildError : public std::exception
{};
   
enum TypeType
{
   WB_TYPE,
   WB_OBJECT,
   WB_MESSAGE
};
   
   
   
class WorldBuilder
{
  public:      
      
   virtual ~WorldBuilder() {}

      
   typedef std::map< std::string, std::string > ExtraInfo;
      
      
   virtual void init( const char * name, int num_types, int num_unique_arrays, const ExtraInfo & xi  ) = 0;
      
      
   virtual void addType( const char      * name, 
                         TypeType          type_type,
                         int               superclass_id,
                         int               num_attributes,
                         int               num_types, // number of unique Type instances used by the attributes
                         const ExtraInfo & xi ) = 0;
      
      
   virtual void addArray( int       array_size, 
                          BasicType btype, 
                          int       type_id,
                          bool      is_basic_type ) = 0;
      
      
   virtual void addVariable ( const char      * name,
                              BasicType         btype,
                              int               type_id, 
                              const ExtraInfo & xi ) = 0;

      
   virtual PWorld finalize() = 0;
      
};

      
}


#endif


