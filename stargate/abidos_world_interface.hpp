#ifndef ABIDOS_WORLD_INTERFACE_H
#define ABIDOS_WORLD_INTERFACE_H

#include <boost/unordered_map.hpp>

#include "abidos_common.hpp"
#include "abidos_world.hpp"


namespace abidos
{

sg::PWorldInterface createWorldInterface( const std::string & name, sg::PWorld world );
    
   
   
class WorldInterface : public sg::WorldInterface
{
   typedef boost::unordered_map< UUID *, Object *, boost::hash<UUID*>, puuid_equal > ObjectMap;
   typedef boost::unordered_map< int, sg::NewObjectCallback > NewObjectCBs;
   typedef std::list< Object * > ObjectList;
   
   World       * m_pWorld;
   sg::PWorld    m_worldRef; // used to ensure the world doesn't get deleted before
                             // this interface.
   std::string   m_name;
   NewObjectCBs  m_newObjectCallBacks;
   ObjectList    m_newObjects; 
   
   
  public:
      
   WorldInterface( const std::string & name, World * pWorld );
   ~WorldInterface();

   void onZeroRefcount();

   const char * getName() { return m_name.c_str(); }

   sg::PObject     createObject( int nTypeId );
   sg::PMessage    createMessage( int nTypeId );
      
   void setNewObjectHandler ( int nTypeId, const sg::NewObjectCallback  & cb );
   void setNewMessageHandler( int nTypeId, const sg::NewMessageCallback & cb );

   void registerAttributeUpdateCallback( const sg::PObject & obj,
                                         const sg::AttributeID & attrId,
                                         const sg::AttributeUpdateCallback & cb );

   void runCallbacks();

   // -------- Internal Methods ------------
   
   void newObjectCreated( Object * po );
      
   void objectUpdated( UUID * puuid );

   World * world() { return m_pWorld; }
};

   

} // end namespace abidos


#endif

