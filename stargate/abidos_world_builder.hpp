#ifndef ABIDOS_WORLD_BUILDER_H
#define ABIDOS_WORLD_BUILDER_H

#include "world_builder.hpp"

#include "abidos_world.hpp"
#include "abidos_data_type.hpp"


namespace abidos
{

sg::WorldBuilder * createWorldBuilder();




class BuildError : public sg::BuildError
{
   std::string err_msg;
      
  public:
   BuildError( const std::string & msg ) : err_msg(msg) {}
      
   ~BuildError() throw () {}
      
   virtual const char * what() const throw()
   {
      return err_msg.c_str();
   }
};
   

typedef sg::WorldBuilder::ExtraInfo ExtraInfo;
   
   
class WorldBuilder : public sg::WorldBuilder
{
   int         m_nNumTotalTypes;
   uint16_t    m_nextTypeId;
   World     * m_pWorld;
      
   struct {
      DataType * pType;
      int        nAttributes;
      int        nComplexTypes;
      bool       bIsObject;
      bool       bIsMessage;
   } m_tinfo;
      
   uint16_t    getNextTypeId()   { return m_nextTypeId;     }
   void        incrementTypeId() { ++m_nextTypeId;          }
   World     * world()           { return m_pWorld;         }
      
   bool worldIsComplete() { return m_pWorld && m_nNumTotalTypes == m_nextTypeId - 1; }
      
   void         finishType();
   PCharStarMap createMap( const ExtraInfo & xi );
      
      
  public:
      
   WorldBuilder();
      
   ~WorldBuilder();
     
      
            
   void init( const char * name, int num_types, int num_unique_arrays, const ExtraInfo & xi  );

      
   virtual void addType( const char      * name,
                         sg::TypeType      type_type,
                         int               superclass_id,
                         int               num_attributes,
                         int               num_types,
                         const ExtraInfo & xi );
      
      
   void addArray( int           array_size, 
                  sg::BasicType btype, 
                  int           type_id, 
                  bool          is_basic_type );

      
   void addVariable ( const char      * name,
                      sg::BasicType     btype,
                      int               type_id,
                      const ExtraInfo & xi );
      
   sg::PWorld finalize();
};
   
   

} // end namespace abidos


#endif

