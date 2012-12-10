
#include <boost/foreach.hpp>

#include "abidos_common.hpp"

namespace abidos
{


AbidosError::AbidosError( const std::string & msg ) : err_msg(msg) {}
      
AbidosError::~AbidosError() throw () {}
      
const char * AbidosError::what() const throw()
{
   return err_msg.c_str();
}



LocalizedPool::LocalizedPool( std::size_t blockSize ) :
      m_pCurrentBlock(0),
      m_numAllocated(0), m_blockSize(blockSize)
{
   allocBlock();
}
   
   
LocalizedPool::~LocalizedPool()
{
   BOOST_FOREACH( uint8_t * p, m_pages )
   {
      delete [] p;
   }
}
   
   
void LocalizedPool::allocBlock()
{
   m_numAllocated  = 0;
   m_pCurrentBlock = new uint8_t[ m_blockSize ];
   m_pages.push_back( m_pCurrentBlock );
       
   memset(m_pCurrentBlock, 0, m_blockSize);
}
      
   
uint8_t * LocalizedPool::allocBytes( int nNumBytes )
{
   if ( m_numAllocated + nNumBytes > m_blockSize )
      allocBlock();
       
   if ( m_numAllocated + nNumBytes > m_blockSize )
      throw AbidosError("Allocation request exceeds block size");
       
   uint8_t * r = &m_pCurrentBlock[ m_numAllocated ];
       
   m_numAllocated += nNumBytes;
       
   // Pad out the allocation so the next will begin at a 4-byte aligned
   // address.
   while ( ((long)&m_pCurrentBlock[ m_numAllocated ]) % 4 != 0 )
      ++m_numAllocated;
       
   return r;
}
   
   
   
} // end namespace abidos

