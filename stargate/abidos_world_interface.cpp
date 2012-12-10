#include <iostream>
#include <boost/foreach.hpp>

#include "abidos_world.hpp"
#include "abidos_world_interface.hpp"
#include "abidos_data_type.hpp"
#include "abidos_data.hpp"

namespace abidos
{

using std::cout;
using std::cerr;
using std::endl;



sg::PWorldInterface createWorldInterface( const std::string & name, sg::PWorld world )
{
   World * w = dynamic_cast< World * >( world.get() );
   
   if (!w)
      return 0;
   
   return new WorldInterface( name, w );
}



WorldInterface::WorldInterface( const std::string & name, World * pWorld ) :
      m_pWorld(pWorld), m_worldRef(pWorld), m_name( name )
{
   m_pWorld->addInterface( this );
}


WorldInterface::~WorldInterface()
{
   m_pWorld->removeInterface( this );
}


void WorldInterface::onZeroRefcount()
{
   cerr << "WorldInterface::onZeroRefcount()" << endl;
}

sg::PObject     WorldInterface::createObject( int nTypeId )
{
   return m_pWorld->createObject( this, nTypeId );
}


sg::PMessage    WorldInterface::createMessage( int nTypeId )
{
   return 0; //m_pWorld->createMessage( nTypeId );
}


void WorldInterface::setNewObjectHandler ( int nTypeId, const sg::NewObjectCallback  & cb)
{
   assert(  nTypeId < m_pWorld->types().size() );
   
   m_newObjectCallBacks[ nTypeId ] = cb;
}


void WorldInterface::setNewMessageHandler( int nTypeId, const sg::NewMessageCallback & cb)
{}


void WorldInterface::registerAttributeUpdateCallback( const sg::PObject & obj,
                                                      const sg::AttributeID & attrId,
                                                      const sg::AttributeUpdateCallback & cb )
{}


void WorldInterface::newObjectCreated( Object * po )
{
   m_newObjects.push_back( po );
}

void WorldInterface::objectUpdated( UUID * puuid )
{}


void WorldInterface::runCallbacks()
{
   int                      type_id;
   const DataType         * pt;
   NewObjectCBs::iterator   i;

   
   if ( ! m_newObjects.empty() )
   {
      NewObjectCBs::iterator global_cb = m_newObjectCallBacks.find( 0 );
      
      BOOST_FOREACH( Object * po, m_newObjects )
      {
         type_id = po->getTypeId();
         pt      = m_pWorld->types()[ type_id ];

         if ( global_cb != m_newObjectCallBacks.end() )
               global_cb->second( po );
   
         while( pt )
         {
            i = m_newObjectCallBacks.find( pt->getTypeId() );
         
            if ( i != m_newObjectCallBacks.end() )
            {
               i->second( po );
               break;
            }
         
            pt = pt->getSuperClass();
         }
      }

      m_newObjects.clear();
   }
}

} // end namespace abidos

