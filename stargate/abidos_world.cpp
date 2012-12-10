#include <iostream>
#include <iomanip>
#include <boost/foreach.hpp>
#include <string.h>

#include "abidos_world.hpp"

#include "abidos_type_encoding.hpp"
#include "abidos_data_type.hpp"
#include "abidos_data.hpp"
#include "abidos_world_interface.hpp"

namespace abidos
{
using std::cout;
using std::cerr;
using std::endl;
using std::setw;

//--------------------------------------------------------------------------
// Object
//
Object::Object( PInstanceControlBlock cb ) : m_cb(cb)
{
   
}

const sg::UUID * Object::getUUID()     const
{
   return m_cb->uuid();
}
   
sg::PInstance Object::getInstance() const
{
   return m_cb->world()->allocateInstance( m_cb, 
                                           m_cb->dataType()->getEncoding(),
                                           m_cb->data(), 
                                           0 );
}
      
void Object::onZeroRefcount()
{
   cerr << "Object refcount reached zero!" << endl;

   m_cb->world()->onZeroRefcount( this );
}

sg::PWorldInterface Object::getOwningInterface() const
{
   return m_cb->getOwningInterface();
}

int Object::getTypeId() const
{
   return m_cb->dataType()->getTypeId();
}

int Object::isType( int nTypeId ) const
{
   return m_cb->dataType()->getEncoding()->getDerivationFrom( (uint16_t) nTypeId );
}

const UUID * Object::getImplUUID()
{
   return m_cb->uuid();
}

//--------------------------------------------------------------------------
// Message
//
Message::Message( PInstanceControlBlock cb ) : m_cb(cb)
{}

const sg::UUID * Message::getUUID()     const
{
   return m_cb->uuid();
}
   
sg::PInstance Message::getInstance() const
{
   return m_cb->world()->allocateInstance( m_cb, 
                                           m_cb->dataType()->getEncoding(), 
                                           m_cb->data(), 
                                           0 );
}
      
void Message::onZeroRefcount()
{
   cerr << "Message refcount reached zero!" << endl;
   m_cb->world()->onZeroRefcount( this );
}


const UUID * Message::getImplUUID()
{
   return m_cb->uuid();
}


//--------------------------------------------------------------------------
// World
//
World::World( const char * pszWorldName, int nNumTypes ) :
      m_pInstanceCache(0)
{
   m_pszName   = cacheString( pszWorldName );

   m_pEncoding = new EncodingTable( nNumTypes );

   m_dataTypes.push_back( 0 ); // Data Type Id 0/index0 is reserved for "no type"

   // Preallocate say.... 200 Instances. This number is chosen at random
   // TODO: make this a tuneable parameter
   //
   Instance * tmp;
       
   for (int i=0; i < 200; i++)
   {
      tmp = new Instance;
           
      tmp->m_pNext = m_pInstanceCache;

      m_pInstanceCache = tmp;
   }
}


World::~World()
{
   cerr << "~~~~~~ World destructor: " << m_pszName << endl;
       
   BOOST_FOREACH( ObjectMap::value_type p, m_objectMap )
   {
      delete [] p.second->m_cb->data();
           
      delete p.second;
   }
       
   BOOST_FOREACH( DataType * p, m_dataTypes )
   {
      delete p;
   }

   Instance *tmp;
       
   while( m_pInstanceCache )
   {
      tmp = m_pInstanceCache->m_pNext;
      delete m_pInstanceCache;
      m_pInstanceCache = tmp;
   }

   delete m_pEncoding;
}


const char * World::getName() const
{
   return m_pszName;
}


const char * World::cacheString( const char * psz )
{
   CharStarMap::iterator i = m_stringCache.find( psz );

   if ( i != m_stringCache.end() )
      return i->second;
   else
   {
      char * pnew = (char *) m_stringPool.allocBytes( strlen(psz) + 1 );

      strcpy(pnew, psz);

      m_stringCache[ pnew ] = pnew;

      return m_stringCache[ pnew ];
   }
}


sg::PInstance  World::allocateInstance( PInstanceControlBlock  cb,
                                        const TypeEncoding    *penc,
                                        uint8_t               *pdat,
                                        uint16_t               voff )
{
   Instance * tmp = m_pInstanceCache;
       
   if (tmp)
      m_pInstanceCache = tmp->m_pNext;
   else
      tmp = new Instance;

   tmp->reset( cb, penc, pdat, voff );
   
   return tmp;
}


void World::deallocateInstance( Instance * pi )
{
   pi->m_pNext = m_pInstanceCache;
   m_pInstanceCache = pi;
}


namespace
{
void printDataType( DataType * pDataType, EncodingTable *pEncoding )
{
   cerr << "-----------------------------------------------------" << endl;
   cerr << "- Id: " << setw(4) << pDataType->getTypeId();
   cerr << " Size: " << setw(4) << pEncoding->getStaticTypeSize( pDataType->getTypeId() );
   cerr << "  Name: " << pDataType->getName();
   if ( pDataType->getSuperClass() )
      cerr << "  Superclass: " << pDataType->getSuperClass()->getName();
   cerr << endl;
   const PCharStarMap xi = pDataType->getExtraInfo();

   if (!xi->empty())
   {
      cerr << "- Extra Info:" << endl;
      CharStarMap::const_iterator i;
      for( i = xi->begin(); i != xi->end(); i++ )
         cerr << "    " << setw(15) << i->first << " = " << i->second << endl;
   }

   cerr << "- Variables: " << endl;

   const TypeEncoding          *pte = pDataType->getEncoding();
   const TypeEncoding::VarInfo *pvi = pte->varInfo();

   for( int i = 0; i < pDataType->getVars().size(); i++ )
   {
      cerr << "    "      << setw(15) << std::left << pDataType->getVars()[i].pszName;
      cerr << " "         << setw(15) << std::left << pEncoding->getTypeName( pvi[i].typeCode );
      cerr << " Offset: " << setw(4) << pvi[i].byteOffset;
      cerr << " Size: "   << setw(4) << pEncoding->getStaticVariableSize( pvi[i].typeCode );
      cerr << " Index: "  << setw(4) << pvi[i].linearIndexOffset;
      cerr << endl;
   }

}
}// end anonymous namespace


void World::printTypes()
{
   BOOST_FOREACH( DataType * p, m_dataTypes )
   {
      if(p)
         printDataType(p, m_pEncoding);
   }
}

void World::onZeroRefcount()
{
   delete this; // suicide
}



Object * World::createObject( WorldInterface *pwi, uint16_t type_id )
{
   assert( type_id < m_dataTypes.size() );

   cerr << "create obj\n";

   DataType           * pdt = m_dataTypes[ type_id ];

   const TypeEncoding * pte = pdt->getEncoding();

   cerr << "Data Size: " << pte->getFullInheritanceStaticSize() << endl;
//       cerr << "Data Size: " << pte->staticSize() << endl;

   int data_size = pte->getFullInheritanceStaticSize();
   uint8_t * pData = new uint8_t[ data_size ];
   uint16_t  nvars = pdt->getTotalNumVars();

   memset( pData, 0, data_size );

   cerr << "sizeICB: " << sizeof(InstanceControlBlock) << endl;

   uint16_t nbytes =  sizeof(InstanceControlBlock) + (nvars/8 + (nvars%8 ? 1:0)) * 3;


   cerr << "Num vars: " << nvars << endl;
   cerr << "nbytes  : " << nbytes << endl;

   int icb_size = InstanceControlBlock::requiredSize( pdt );
   uint8_t * pBuff = new uint8_t[ icb_size ];

   memset( pBuff, 0, icb_size );

   InstanceControlBlock * pcb = new ( pBuff ) InstanceControlBlock( pwi, pdt, pData );

   Object * po = new Object( pcb );

   cerr << "create obj done\n";

   m_objectMap[ po->getImplUUID() ] = po;


   BOOST_FOREACH( WorldInterface * wi, m_interfaces )
   {
      if ( wi != pwi ) // don't register callback for creating interface
         wi->newObjectCreated( po );
   }
   

   return po;
}



void World::onZeroRefcount( Object * obj )
{
   ObjectMap::iterator p = m_objectMap.find( obj->getImplUUID() );

   assert( p != m_objectMap.end() );

   cerr << "~~~ Erasing Object due to zero Refcount! ~~~" << endl;
   
   delete [] p->second->m_cb->data();
           
   delete p->second;

   m_objectMap.erase( p );
}


void World::onZeroRefcount( Message * msg )
{
   delete msg;
}


void World::addInterface( WorldInterface * pwi )
{
   m_interfaces.push_back( pwi );
}


void World::removeInterface( WorldInterface * pwi )
{
   for( InterfaceList::iterator i = m_interfaces.begin();
        i != m_interfaces.end();
        i++ )
   {
      if ( (*i) == pwi )
      {
         m_interfaces.erase(i);
         break;
      }
   }
}



} // end namespace abidos

